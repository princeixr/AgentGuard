"""Validated, atomic publication for the active FirewallV2 policy."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentguard.firewall_v2.policy.loader import LoadedPolicy, PolicyLoader
from agentguard.firewall_v2.policy.models import PolicyDocumentV1
from agentguard.firewall_v2.policy.resolver import resolve_demo_policy
from agentguard.firewall_v2.policy.validator import (
    PolicyValidationError,
    validate_policy_scope,
)

_POLICY_WRITE_LOCK = threading.Lock()


class PolicyConflictError(PolicyValidationError):
    """Raised when a client attempts to replace a policy it did not read."""


class PolicyStore:
    def __init__(self, loader: PolicyLoader | None = None):
        self.loader = loader or PolicyLoader()

    def publish(
        self,
        document: dict[str, Any],
        *,
        expected_hash: str,
    ) -> LoadedPolicy:
        with _POLICY_WRITE_LOCK:
            current = resolve_demo_policy(self.loader)
            if current.effective_hash != expected_hash:
                raise PolicyConflictError(
                    "The active policy changed after this editor was opened. "
                    "Reload it before saving."
                )

            try:
                candidate = PolicyDocumentV1.model_validate(document)
            except ValidationError as exc:
                raise PolicyValidationError(f"Policy document is invalid: {exc}") from exc

            validate_policy_scope(
                candidate,
                workspace_id=current.document.scope.workspace_id,
                agent_id=current.document.scope.agent_id,
                deployment_id=current.document.scope.deployment_id,
            )
            if candidate.policy_id != current.document.policy_id:
                raise PolicyValidationError("The assigned policy ID cannot be changed.")
            if candidate.scope != current.document.scope:
                raise PolicyValidationError("The assigned policy scope cannot be changed.")

            published = candidate.model_copy(
                update={
                    "version": _next_patch_version(current.document.version),
                    "status": "published",
                }
            )
            _atomic_write_policy(current.path, published)
            return resolve_demo_policy(self.loader)


def _next_patch_version(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _atomic_write_policy(path: Path, document: PolicyDocumentV1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document.model_dump(mode="json"), indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise PolicyValidationError(f"Unable to publish policy {path}: {exc}") from exc
