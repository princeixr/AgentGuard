"""AgentGuard exception types."""


class AgentGuardError(Exception):
    """Base exception for AgentGuard errors."""


class ContractValidationError(AgentGuardError):
    """Raised when data does not satisfy the shared contract."""

