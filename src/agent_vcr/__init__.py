"""
agent-vcr: Deterministic record and replay for LLM agent tool calls and completions.
"""

from agent_vcr.cassette import Cassette
from agent_vcr.engine import (
    get_active_cassette,
    record_or_replay,
    record_or_replay_async,
    record_tool,
    use_cassette,
)
from agent_vcr.exceptions import (
    AgentVCRError,
    CannotOverwriteExistingCassetteError,
    CassetteNotFoundError,
    UnhandledInteractionError,
)
from agent_vcr.matchers import (
    DEFAULT_MATCHERS,
    RequestMatcher,
    match_call_type,
    match_name,
    match_payload,
)
from agent_vcr.models import (
    Interaction,
    InteractionRequest,
    InteractionResponse,
    RecordMode,
)
from agent_vcr.sanitizers import REDACTED_PLACEHOLDER, Sanitizer

__version__ = "0.1.0"

__all__ = [
    "Cassette",
    "use_cassette",
    "get_active_cassette",
    "record_or_replay",
    "record_or_replay_async",
    "record_tool",
    "RecordMode",
    "Interaction",
    "InteractionRequest",
    "InteractionResponse",
    "Sanitizer",
    "REDACTED_PLACEHOLDER",
    "RequestMatcher",
    "match_call_type",
    "match_name",
    "match_payload",
    "DEFAULT_MATCHERS",
    "AgentVCRError",
    "CassetteNotFoundError",
    "CannotOverwriteExistingCassetteError",
    "UnhandledInteractionError",
]
