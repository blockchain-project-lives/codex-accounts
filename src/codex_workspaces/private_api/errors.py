from __future__ import annotations


SENSITIVE_WORDS = (
    "access_token",
    "refresh_token",
    "id_token",
    "session_token",
    "authorization",
    "cookie",
    "api_key",
    "bearer",
    "token",
)


class PrivateApiError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(redact_sensitive_text(message))
        self.message = redact_sensitive_text(message)


class PrivateApiDisabledError(PrivateApiError):
    pass


class PrivateApiAuthError(PrivateApiError):
    pass


class PrivateApiRateLimitedError(PrivateApiError):
    pass


class PrivateApiForbiddenError(PrivateApiError):
    pass


class PrivateApiUnsupportedResponseError(PrivateApiError):
    pass


class PrivateApiNetworkError(PrivateApiError):
    pass


def redact_sensitive_text(text: str) -> str:
    redacted = text
    for word in SENSITIVE_WORDS:
        redacted = redacted.replace(word, "[redacted]")
        redacted = redacted.replace(word.upper(), "[redacted]")
    return redacted
