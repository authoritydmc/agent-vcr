"""Sensitive data scrubbing and sanitization utilities."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Pattern, Sequence, Union

DEFAULT_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
    "client_secret",
    "x_api_key",
    "x_auth_token",
    "session_token",
    "bearer",
    "cookie",
    "set_cookie",
    "credentials",
    "id_token",
}

DEFAULT_SCRUB_PATTERNS: List[Pattern[str]] = [
    # Authorization header / Bearer token
    re.compile(r"((?i:Bearer\s+))[A-Za-z0-9_\-\.]{15,}"),
    re.compile(r"((?i:Authorization:\s*(?:Bearer\s+)?))[A-Za-z0-9_\-\.]{15,}"),
    re.compile(r"((?i:x-api-key:\s*))[A-Za-z0-9_\-\.]{15,}"),
    # OpenAI tokens
    re.compile(r"\b(sk-proj-[a-zA-Z0-9_\-]{20,})\b"),
    re.compile(r"\b(sk-admin-[a-zA-Z0-9_\-]{20,})\b"),
    re.compile(r"\b(sk-svcacct-[a-zA-Z0-9_\-]{20,})\b"),
    re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b"),
    re.compile(r"\b(org-[a-zA-Z0-9]{24})\b"),
    # Anthropic tokens
    re.compile(r"\b(sk-ant-api\d{2}-[a-zA-Z0-9_\-]{20,})\b"),
    re.compile(r"\b(sk-ant-[a-zA-Z0-9_\-]{20,})\b"),
    # GitHub tokens
    re.compile(r"\b(github_pat_[a-zA-Z0-9_]{50,})\b"),
    re.compile(r"\b(gh[pousr]_[a-zA-Z0-9]{36,})\b"),
    # Slack tokens
    re.compile(r"\b(xox[baprs]-[0-9a-zA-Z\-]{10,})\b"),
    # URL query parameter keys
    re.compile(r"((?i:[?&](?:api_key|apikey|token|access_token|key|secret|password|auth|refresh_token)=))([^&\s]+)"),
]

REDACTED_PLACEHOLDER = "[REDACTED]"


class Sanitizer:
    """Scrubs sensitive strings and keys from interaction payloads and metadata."""

    def __init__(
        self,
        sensitive_keys: Union[Sequence[str], None] = None,
        custom_patterns: Union[Sequence[Union[str, Pattern[str]]], None] = None,
        custom_scrubber: Union[Callable[[Any], Any], None] = None,
    ):
        raw_keys = sensitive_keys if sensitive_keys is not None else DEFAULT_SENSITIVE_KEYS
        self.sensitive_keys = set(self._normalize_key(k) for k in raw_keys)
        self.patterns: List[Pattern[str]] = list(DEFAULT_SCRUB_PATTERNS)
        if custom_patterns:
            for pat in custom_patterns:
                if isinstance(pat, str):
                    self.patterns.append(re.compile(pat))
                else:
                    self.patterns.append(pat)
        self.custom_scrubber = custom_scrubber

    @staticmethod
    def _normalize_key(key: Any) -> str:
        return str(key).lower().replace("-", "_")

    def _is_sensitive_key(self, key: Any) -> bool:
        normalized = self._normalize_key(key)
        return normalized in self.sensitive_keys

    def sanitize(self, data: Any) -> Any:
        """Recursively scrub sensitive keys and regex matches from data structures."""
        if self.custom_scrubber:
            data = self.custom_scrubber(data)

        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                if self._is_sensitive_key(k):
                    sanitized_dict[k] = REDACTED_PLACEHOLDER
                else:
                    sanitized_dict[k] = self.sanitize(v)
            return sanitized_dict

        elif isinstance(data, (list, tuple)):
            res = [self.sanitize(item) for item in data]
            return tuple(res) if isinstance(data, tuple) else res

        elif isinstance(data, str):
            val = data
            for pat in self.patterns:
                if pat.groups >= 2:
                    val = pat.sub(r"\g<1>" + REDACTED_PLACEHOLDER, val)
                elif pat.groups == 1:
                    # If pattern is a prefix group e.g. (Bearer ), keep prefix and redact rest
                    if pat.pattern.startswith("((?i:") or pat.pattern.startswith("(Bearer") or pat.pattern.startswith("(("):
                        val = pat.sub(r"\g<1>" + REDACTED_PLACEHOLDER, val)
                    else:
                        val = pat.sub(REDACTED_PLACEHOLDER, val)
                else:
                    val = pat.sub(REDACTED_PLACEHOLDER, val)
            return val

        return data

