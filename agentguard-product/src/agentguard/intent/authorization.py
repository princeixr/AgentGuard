"""Deterministic authorization of normalized actions against user intent."""

from __future__ import annotations

import os

from agentguard.firewall_v2.tools.normalizers.models import NormalizedActionV1
from agentguard.intent.models import IntentAuthorizationV1, IntentContractV2


def authorize_action(
    contract: IntentContractV2,
    action: NormalizedActionV1,
    *,
    confidence_threshold: float = 0.70,
) -> IntentAuthorizationV1:
    capabilities = set(action.capabilities)
    requested = capabilities.intersection(contract.requested_capabilities)
    forbidden = capabilities.intersection(contract.forbidden_capabilities)
    unauthorized = capabilities.difference(contract.requested_capabilities)
    unauthorized.discard("unknown")

    matched_resources = [
        resource.value
        for resource in action.resources
        if any(
            _resource_matches(resource.value, allowed)
            for allowed in contract.permitted_resources
        )
    ]
    forbidden_resources = [
        resource.value
        for resource in action.resources
        if any(
            _resource_matches(resource.value, denied)
            for denied in contract.forbidden_resources
        )
    ]
    destination_values = {item.value.lower() for item in action.destinations}
    allowed_destinations = {item.lower() for item in contract.destinations}
    destination_violations = sorted(
        destination_values.difference(allowed_destinations)
        if allowed_destinations
        else destination_values
        if action.external_impact
        else set()
    )

    if forbidden or forbidden_resources:
        recommendation = "block"
        explanation = (
            "The proposed action violates an explicit user prohibition in the "
            "turn-scoped intent contract."
        )
    elif destination_violations:
        recommendation = "require_approval"
        explanation = (
            "The proposed action targets a destination not authorized by the user."
        )
    elif (
        action.side_effect
        and action.parser.status not in {"unsupported", "invalid"}
        and (not contract.side_effect_authorized or unauthorized)
    ):
        recommendation = "require_approval"
        explanation = (
            "The proposed side effect was not explicitly authorized by the user."
        )
    elif (
        action.resources
        and contract.permitted_resources
        and len(matched_resources) != len(action.resources)
    ):
        recommendation = "require_approval"
        explanation = "The proposed resource scope exceeds the user's authorization."
    elif (
        contract.extractor.confidence < confidence_threshold
        and action.side_effect
        and action.parser.status not in {"unsupported", "invalid"}
    ):
        recommendation = "require_approval"
        explanation = (
            "Intent extraction confidence is too low to authorize a side effect."
        )
    elif unauthorized and (action.side_effect or action.external_impact):
        recommendation = "require_approval"
        explanation = (
            "The proposed capability was not included in the user's requested actions."
        )
    else:
        recommendation = "allow"
        explanation = (
            "The proposed capabilities and scope are authorized by the turn-scoped "
            "intent contract."
        )

    return IntentAuthorizationV1(
        intent_id=contract.intent_id,
        recommendation=recommendation,
        matched_requested_capabilities=sorted(requested),
        matched_forbidden_capabilities=sorted(forbidden),
        unauthorized_capabilities=sorted(unauthorized),
        matched_resources=matched_resources,
        forbidden_resources=forbidden_resources,
        destination_violations=destination_violations,
        explanation=explanation,
    )


def _resource_matches(value: str, configured: str) -> bool:
    normalized_value = os.path.normpath(os.path.expanduser(value))
    normalized_configured = os.path.normpath(os.path.expanduser(configured))
    return (
        normalized_value == normalized_configured
        or normalized_value.startswith(normalized_configured + os.sep)
    )
