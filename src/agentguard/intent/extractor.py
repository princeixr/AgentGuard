"""Structured LLM intent extraction with deterministic conservative fallback."""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Protocol
from uuid import uuid4

from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.intent.models import (
    IntentConstraintV1,
    IntentContractV2,
    IntentExtractionPayloadV1,
    IntentExtractorEvidenceV1,
)

PROMPT_VERSION = "intent_contract_v1.0.0"
DEFAULT_MODEL = "gemini-2.5-flash"


class IntentProvider(Protocol):
    def extract(
        self,
        user_request: str,
        tool_descriptors: list[ToolDescriptorV1],
    ) -> IntentExtractionPayloadV1:
        ...


class GeminiIntentProvider:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.model = model or os.environ.get("AGENTGUARD_INTENT_MODEL", DEFAULT_MODEL)
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.timeout_seconds = timeout_seconds or float(
            os.environ.get("AGENTGUARD_INTENT_TIMEOUT_SECONDS", "8")
        )

    def extract(
        self,
        user_request: str,
        tool_descriptors: list[ToolDescriptorV1],
    ) -> IntentExtractionPayloadV1:
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is required for structured intent extraction."
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is required for structured intent extraction."
            ) from exc

        client = genai.Client(api_key=self.api_key)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            client.models.generate_content,
            model=self.model,
            contents=_prompt(user_request, tool_descriptors),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=IntentExtractionPayloadV1,
                max_output_tokens=1800,
                candidate_count=1,
            ),
        )
        try:
            response = future.result(timeout=self.timeout_seconds)
        except TimeoutError as exc:
            executor.shutdown(wait=False, cancel_futures=True)
            raise RuntimeError(
                f"Intent extraction timed out after {self.timeout_seconds}s."
            ) from exc
        else:
            executor.shutdown(wait=False, cancel_futures=True)
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, IntentExtractionPayloadV1):
            return parsed
        return IntentExtractionPayloadV1.model_validate_json(
            getattr(response, "text", "") or "{}"
        )


class IntentExtractor:
    def __init__(
        self,
        provider: IntentProvider | None = None,
        *,
        llm_enabled: bool = True,
    ):
        self.provider = provider or GeminiIntentProvider()
        self.llm_enabled = llm_enabled

    def extract(
        self,
        *,
        user_request: str,
        session_id: str,
        agent_id: str,
        tool_descriptors: list[ToolDescriptorV1],
        turn_id: str | None = None,
    ) -> IntentContractV2:
        provider_error: str | None = None
        if self.llm_enabled:
            try:
                payload = self.provider.extract(user_request, tool_descriptors)
                return _contract(
                    payload,
                    user_request=user_request,
                    session_id=session_id,
                    agent_id=agent_id,
                    turn_id=turn_id,
                    evidence=IntentExtractorEvidenceV1(
                        name="gemini_structured_intent",
                        version=PROMPT_VERSION,
                        model=getattr(self.provider, "model", None),
                        method="llm_structured",
                        status="completed",
                        confidence=payload.confidence,
                        detail=(
                            "Structured language model extraction completed and "
                            "passed schema validation."
                        ),
                    ),
                )
            except Exception as exc:
                provider_error = str(exc)

        payload = deterministic_intent_fallback(user_request, tool_descriptors)
        detail = "Deterministic fallback extracted explicit actions and entities."
        if provider_error:
            detail += f" LLM extraction was unavailable: {provider_error}"
        return _contract(
            payload,
            user_request=user_request,
            session_id=session_id,
            agent_id=agent_id,
            turn_id=turn_id,
            evidence=IntentExtractorEvidenceV1(
                name="deterministic_intent_fallback",
                version="1.0.0",
                method="deterministic_fallback",
                status="fallback",
                confidence=payload.confidence,
                detail=detail,
            ),
        )


def deterministic_intent_fallback(
    user_request: str,
    tool_descriptors: list[ToolDescriptorV1],
) -> IntentExtractionPayloadV1:
    text = user_request.lower()
    requested: set[str] = set()
    forbidden: set[str] = set()
    constraints: list[IntentConstraintV1] = []

    aliases = {
        "email.search": (
            "find email",
            "find the latest email",
            "search email",
            "look for email",
        ),
        "email.read": ("read email", "summarize email", "latest email"),
        "email.draft": ("draft", "prepare a reply", "write a reply"),
        "email.send": ("send email", "send it", "email them"),
        "filesystem.inspect": ("list files", "show files", "current directory", "pwd"),
        "filesystem.read": ("read file", "show file", "open file", "cat "),
        "filesystem.write": ("create file", "write file", "make a file", "mkdir", "touch "),
        "filesystem.delete": ("delete file", "delete folder", "remove file", "remove folder", "rm "),
        "calendar.read": ("show calendar", "check calendar", "calendar events"),
        "calendar.create": ("create event", "schedule meeting", "add to calendar"),
        "calendar.update": ("update event", "reschedule"),
        "calendar.delete": ("delete event", "cancel event"),
        "web.search": ("web search", "search the web", "look up"),
        "process.execute": ("run ", "execute "),
    }
    known_capabilities = {
        capability
        for descriptor in tool_descriptors
        for capability in descriptor.capabilities
        if capability != "unknown"
    }
    for capability, phrases in aliases.items():
        if any(phrase in text for phrase in phrases):
            requested.add(capability)
    if "do not send" in text or "don't send" in text or "draft only" in text:
        forbidden.add("email.send")
        requested.discard("email.send")
        constraints.append(
            IntentConstraintV1(
                type="negative_action",
                text="Do not send",
                capability="email.send",
            )
        )
    requested.update(
        capability
        for capability in known_capabilities
        if capability.split(".")[-1].replace("_", " ") in text
    )
    requested.difference_update(forbidden)
    resources = sorted(set(_PATH_PATTERN.findall(user_request)))
    destinations = sorted(set(_EMAIL_PATTERN.findall(user_request)))
    side_effect_authorized = any(
        capability.split(".")[-1]
        in {"write", "delete", "create", "update", "send", "execute", "draft"}
        for capability in requested
    )
    confidence = 0.72 if requested or forbidden or resources or destinations else 0.35
    uncertainties = [] if confidence >= 0.7 else [
        "The deterministic fallback could not resolve a concrete capability."
    ]
    return IntentExtractionPayloadV1(
        requested_capabilities=sorted(requested),
        forbidden_capabilities=sorted(forbidden),
        permitted_resources=resources,
        destinations=destinations,
        side_effect_authorized=side_effect_authorized,
        confirmation_language_present=any(
            phrase in text for phrase in ("confirm", "ask me", "approval")
        ),
        constraints=constraints,
        confidence=confidence,
        uncertainties=uncertainties,
    )


def _contract(
    payload: IntentExtractionPayloadV1,
    *,
    user_request: str,
    session_id: str,
    agent_id: str,
    turn_id: str | None,
    evidence: IntentExtractorEvidenceV1,
) -> IntentContractV2:
    return IntentContractV2(
        turn_id=turn_id or f"turn_{uuid4().hex}",
        session_id=session_id,
        agent_id=agent_id,
        raw_user_request=user_request,
        requested_capabilities=sorted(set(payload.requested_capabilities)),
        forbidden_capabilities=sorted(set(payload.forbidden_capabilities)),
        permitted_resources=sorted(set(payload.permitted_resources)),
        forbidden_resources=sorted(set(payload.forbidden_resources)),
        destinations=sorted(set(payload.destinations)),
        side_effect_authorized=payload.side_effect_authorized,
        confirmation_language_present=payload.confirmation_language_present,
        constraints=payload.constraints,
        uncertainties=payload.uncertainties,
        extractor=evidence,
    )


def _prompt(
    user_request: str,
    tool_descriptors: list[ToolDescriptorV1],
) -> str:
    descriptor_packet = [
        {
            "tool_name": item.tool_name,
            "description": item.description,
            "domain": item.domain,
            "operation": item.operation,
            "capabilities": item.capabilities,
            "side_effect": item.side_effect,
            "external_impact": item.external_impact,
        }
        for item in tool_descriptors
    ]
    return (
        "You are AgentGuard's intent extraction model. Convert only the user's "
        "authorization into the required structured schema. The proposed tool call is "
        "not available and must not influence this contract. Use only capabilities in "
        "the registry when possible. Explicit negative language must populate "
        "forbidden_capabilities. 'Draft only', 'do not send', or equivalent language "
        "must forbid email.send. Do not infer broad authorization from a narrow request. "
        "If authorization is ambiguous, lower confidence and describe uncertainties. "
        f"User request:\n{user_request}\n"
        f"Tool registry:\n{json.dumps(descriptor_packet, sort_keys=True)}"
    )


_PATH_PATTERN = re.compile(
    r"(?:~?/|\.{1,2}/)[A-Za-z0-9_./* -]+|[A-Za-z0-9_.-]+\.(?:txt|json|yaml|yml|md|py|csv)"
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
