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
}

DEFAULT_SCRUB_PATTERNS: List[Pattern[str]] = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE),
    re.compile(r"(ghp_[a-zA-Z0-9]{30,})", re.IGNORECASE),
    re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,})", re.IGNORECASE),
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
        self.sensitive_keys = set(k.lower() for k in (sensitive_keys or DEFAULT_SENSITIVE_KEYS))
        self.patterns: List[Pattern[str]] = list(DEFAULT_SCRUB_PATTERNS)
        if custom_patterns:
            for pat in custom_patterns:
                if isinstance(pat, str):
                    self.patterns.append(re.compile(pat))
                else:
                    self.patterns.append(pat)
        self.custom_scrubber = custom_scrubber

    def sanitize(self, data: Any) -> Any:
        """Recursively scrub sensitive keys and regex matches from data structures."""
        if self.custom_scrubber:
            data = self.custom_scrubber(data)

        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                if str(k).lower() in self.sensitive_keys:
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
                val = pat.sub(r"\1" + REDACTED_PLACEHOLDER if r"\1" in pat.pattern else REDACTED_PLACEHOLDER, val)
            return val

        return data
