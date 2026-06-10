"""Metadata-driven normalizer for structured function and MCP tools."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from agentguard.firewall_v2.tools.models import ToolDescriptorV1
from agentguard.firewall_v2.tools.normalizers.models import (
    NormalizedActionV1,
    NormalizedDestinationV1,
    NormalizedResourceV1,
    ParserResultV1,
)
from agentguard.tracing.schema_v1 import AgentGuardTraceV1

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
SECRET_PATTERN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|private[_-]?key|password|secret)\s*[:=]",
    re.I,
)
FINANCIAL_PATTERN = re.compile(
    r"\b(?:account|routing|invoice|payment|credit card|bank)\b",
    re.I,
)
PII_PATTERN = re.compile(
    r"\b(?:ssn|social security|passport|date of birth|phone number)\b",
    re.I,
)


class StructuredToolNormalizerV1:
    name = "structured_v1"
    version = "1.0.0"

    def normalize(
        self,
        trace: AgentGuardTraceV1,
        descriptor: ToolDescriptorV1,
    ) -> NormalizedActionV1:
        arguments = trace.proposed_tool_call.arguments
        missing = [
            name
            for name in descriptor.required_arguments
            if name not in arguments or arguments[name] is None
        ]
        if missing:
            return self._invalid(
                trace,
                descriptor,
                f"Required arguments are missing: {', '.join(missing)}.",
            )

        resources = [
            NormalizedResourceV1(
                type=_resource_type(descriptor.category, value),
                value=value,
                access=descriptor.operation,
                sensitivity=_resource_sensitivity(value),
            )
            for value in _role_values(
                arguments,
                descriptor.argument_roles.get("resources", []),
            )
        ]
        destinations = [
            _destination(value, descriptor.external_impact)
            for value in _role_values(
                arguments,
                descriptor.argument_roles.get("destinations", []),
            )
        ]
        data_values = _role_values(
            arguments,
            descriptor.argument_roles.get("data", []),
        )
        data_classes = sorted(
            set(descriptor.declared_data_classes)
            | _detect_data_classes(data_values)
            | _detect_data_classes([item.value for item in destinations])
        )
        estimated_value = _first_number(
            arguments,
            descriptor.argument_roles.get("estimated_value", []),
        )
        currency = _first_text(
            arguments,
            descriptor.argument_roles.get("currency", []),
        )
        confidence = descriptor.metadata_confidence
        flags: list[str] = []
        if descriptor.external_impact:
            flags.append("external_impact")
        if descriptor.reversible is False:
            flags.append("irreversible")
        if any(resource.sensitivity == "sensitive" for resource in resources):
            flags.append("sensitive_resource")
        if data_classes:
            flags.append("sensitive_data_detected")
        if confidence < 0.7:
            flags.append("low_metadata_confidence")

        return NormalizedActionV1(
            trace_id=trace.trace_id,
            tool_name=descriptor.tool_name,
            domain=descriptor.domain,
            capabilities=descriptor.capabilities,
            operation=descriptor.operation,
            resources=resources,
            destinations=destinations,
            side_effect=descriptor.side_effect is not None,
            reversible=descriptor.reversible,
            impact=(
                descriptor.impact
                if descriptor.impact in {"low", "medium", "high"}
                else "unknown"
            ),
            data_classes=data_classes,
            external_impact=descriptor.external_impact,
            privilege_level=descriptor.privilege_level,
            estimated_value=estimated_value,
            estimated_value_currency=currency,
            flags=sorted(set(flags)),
            parser=ParserResultV1(
                name=self.name,
                version=self.version,
                status="parsed" if confidence >= 0.8 else "partial",
                confidence=confidence,
                unsupported_syntax=False,
                detail=(
                    f"Normalized {descriptor.tool_name} from its security descriptor "
                    f"as {descriptor.domain}.{descriptor.operation}."
                ),
            ),
            argument_hash=trace.proposed_tool_call.argument_hash,
        )

    def _invalid(
        self,
        trace: AgentGuardTraceV1,
        descriptor: ToolDescriptorV1,
        detail: str,
    ) -> NormalizedActionV1:
        return NormalizedActionV1(
            trace_id=trace.trace_id,
            tool_name=descriptor.tool_name,
            domain=descriptor.domain,
            capabilities=descriptor.capabilities or ["unknown"],
            operation=descriptor.operation,
            side_effect=descriptor.side_effect is not None,
            reversible=descriptor.reversible,
            impact="unknown",
            external_impact=descriptor.external_impact,
            privilege_level=descriptor.privilege_level,
            flags=["invalid_arguments"],
            parser=ParserResultV1(
                name=self.name,
                version=self.version,
                status="invalid",
                confidence=0.0,
                detail=detail,
            ),
            argument_hash=trace.proposed_tool_call.argument_hash,
        )


def _role_values(arguments: dict[str, Any], fields: list[str]) -> list[str]:
    values: list[str] = []
    for field in fields:
        if field in arguments:
            values.extend(_string_values(arguments[field]))
    return list(dict.fromkeys(value for value in values if value))


def _string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value.strip()
    elif isinstance(value, (int, float)):
        yield str(value)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)


def _resource_type(category: str, value: str) -> str:
    if category == "file" and ("/" in value or value.startswith("~")):
        return "filesystem_path"
    return "unknown"


def _resource_sensitivity(value: str) -> str:
    lowered = value.lower()
    sensitive_tokens = (
        ".ssh",
        "credential",
        "private",
        "secret",
        "wallet",
        "keychain",
        "/etc",
    )
    return "sensitive" if any(token in lowered for token in sensitive_tokens) else "normal"


def _destination(value: str, external_impact: bool | None) -> NormalizedDestinationV1:
    if EMAIL_PATTERN.fullmatch(value):
        destination_type = "email"
    elif "://" in value:
        destination_type = "url"
    elif "." in value and " " not in value:
        parsed = urlparse(f"//{value}")
        destination_type = "host" if parsed.hostname else "domain"
    else:
        destination_type = "unknown"
    return NormalizedDestinationV1(
        type=destination_type,
        value=value,
        external=external_impact,
    )


def _detect_data_classes(values: list[str]) -> set[str]:
    text = "\n".join(values)
    classes: set[str] = set()
    if EMAIL_PATTERN.search(text):
        classes.add("email_address")
    if SECRET_PATTERN.search(text):
        classes.add("credential_or_secret")
    if FINANCIAL_PATTERN.search(text):
        classes.add("financial")
    if PII_PATTERN.search(text):
        classes.add("pii")
    return classes


def _first_number(arguments: dict[str, Any], fields: list[str]) -> float | None:
    for field in fields:
        value = arguments.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
            if match:
                return float(match.group(0))
    return None


def _first_text(arguments: dict[str, Any], fields: list[str]) -> str | None:
    for field in fields:
        value = arguments.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
