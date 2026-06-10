"""Load immutable policy versions from checked-in JSON documents."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pydantic import ValidationError

from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.policy.validator import PolicyValidationError, validate_policy_scope


class LoadedPolicy:
    def __init__(self, document: PolicyDocumentV1, path: Path, raw_text: str):
        self.document = document
        self.path = path
        self.raw_text = raw_text
        canonical = json.dumps(
            document.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        self.effective_hash = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


class PolicyLoader:
    def __init__(self, default_path: Path | None = None):
        configured = os.environ.get("AGENTGUARD_POLICY_PATH")
        self.default_path = _resolve_default_policy_path(configured or default_path)

    def load(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        deployment_id: str | None = None,
        path: Path | None = None,
    ) -> LoadedPolicy:
        policy_path = path or self.default_path
        if not policy_path.is_absolute():
            policy_path = _repo_root() / policy_path
        try:
            raw_text = policy_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PolicyValidationError(
                f"Unable to read policy document {policy_path}: {exc}"
            ) from exc
        try:
            payload = json.loads(raw_text)
            document = PolicyDocumentV1.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise PolicyValidationError(
                f"Policy document {policy_path} is invalid: {exc}"
            ) from exc
        validate_policy_scope(
            document,
            workspace_id=workspace_id,
            agent_id=agent_id,
            deployment_id=deployment_id,
        )
        if document.status != "published":
            raise PolicyValidationError(
                f"Policy {document.policy_id}@{document.version} is not published."
            )
        return LoadedPolicy(document=document, path=policy_path, raw_text=raw_text)


def _resolve_default_policy_path(configured: str | Path | None) -> Path:
    if configured:
        return Path(configured)
    candidates = [
        Path.cwd() / "policies" / "personal_assistant_v1.json",
        _repo_root() / "policies" / "personal_assistant_v1.json",
        Path("/app/policies/personal_assistant_v1.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
