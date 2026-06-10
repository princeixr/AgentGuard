"""Minimal redaction utilities for traces before public release."""


def redact_secret_like_text(value: str) -> str:
    lowered = value.lower()
    if "secret" in lowered or "token" in lowered or "password" in lowered:
        return "[REDACTED]"
    return value
