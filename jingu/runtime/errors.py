"""Runtime exceptions."""


class JinguRuntimeError(Exception):
    """Base exception for runtime failures."""


class NotFoundError(JinguRuntimeError):
    """Raised when a referenced runtime object does not exist."""


class GuardrailViolation(JinguRuntimeError):
    """Raised when an operation violates a runtime guardrail."""


class InvalidTransitionError(GuardrailViolation):
    """Raised when a job state transition is not allowed."""
