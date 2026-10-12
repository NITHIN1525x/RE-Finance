import logging
import re

# Values of these query parameters are credentials or identifiers that must not reach logs:
# `code` (a one-time OAuth authorization code), `state` (CSRF nonce), `realmId` (full company ID).
_SENSITIVE_QS = re.compile(r"(?i)\b(code|state|realmId|refresh_token|access_token)=([^&\s\"']+)")


def redact(text):
    return _SENSITIVE_QS.sub(lambda m: f"{m.group(1)}=[redacted]", text)


class RedactOAuthParams(logging.Filter):
    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never break logging
            return True
        cleaned = redact(message)
        if cleaned != message:
            record.msg, record.args = cleaned, None
        return True
