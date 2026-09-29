"""Matching strategies for incoming requests against recorded interactions."""

from __future__ import annotations

import json
from typing import Any, Callable, List, Optional
from agent_vcr.models import InteractionRequest

MatcherFunction = Callable[[InteractionRequest, InteractionRequest], bool]


def match_call_type(req1: InteractionRequest, req2: InteractionRequest) -> bool:
    """Matches call_type exactly (e.g. 'tool', 'llm', 'function')."""
    return req1.call_type == req2.call_type


def match_name(req1: InteractionRequest, req2: InteractionRequest) -> bool:
    """Matches the target tool/model name."""
    return req1.name == req2.name


def match_payload(req1: InteractionRequest, req2: InteractionRequest) -> bool:
    """Matches JSON payload / arguments equivalence."""
    def _normalize(val: Any) -> str:
        try:
            return json.dumps(val, sort_keys=True)
        except (TypeError, ValueError):
            return str(val)

    return _normalize(req1.payload) == _normalize(req2.payload)


DEFAULT_MATCHERS: List[MatcherFunction] = [
    match_call_type,
    match_name,
    match_payload,
]


class RequestMatcher:
    """Evaluates whether an incoming request matches a recorded request using configured matchers."""

    def __init__(self, matchers: Optional[List[MatcherFunction]] = None):
        self.matchers = matchers if matchers is not None else list(DEFAULT_MATCHERS)

    def matches(self, incoming: InteractionRequest, recorded: InteractionRequest) -> bool:
        """Returns True if all configured matchers evaluate to True."""
        for matcher in self.matchers:
            if not matcher(incoming, recorded):
                return False
        return True
