"""Shared enums used across AgentGuard subsystems."""

from enum import Enum


class Verdict(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REVIEW = "review"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


class FailureType(str, Enum):
    NONE = "none"
    INTENT_DRIFT = "intent_drift"
    SCOPE_CREEP = "scope_creep"
    ARGUMENT_DRIFT = "argument_drift"
    PREMATURE_IRREVERSIBLE_ACTION = "premature_irreversible_action"
    PROMPT_INJECTION_FROM_TOOL_OUTPUT = "prompt_injection_from_tool_output"
    BENIGN_TO_DANGEROUS_CHAIN = "benign_to_dangerous_chain"
    EXCESSIVE_AGENCY = "excessive_agency"
    DATA_MINIMIZATION_FAILURE = "data_minimization_failure"


class ToolRiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW_SIDE_EFFECT = "low_side_effect"
    EXTERNAL_WRITE = "external_write"
    IRREVERSIBLE = "irreversible"
    HIGH_RISK = "high_risk"

