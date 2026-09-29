"""Data models for interactions and cassettes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RecordMode(str, Enum):
    """Cassette recording modes."""
    ONCE = "once"                 # Record if file does not exist, replay otherwise
    ALL = "all"                   # Overwrite / record all interactions every time
    NONE = "none"                 # Replay only; raise exception if unmatched or missing
    NEW_EPISODES = "new_episodes" # Replay matched interactions, record new ones


@dataclass
class InteractionRequest:
    """Represents a request sent to a tool or LLM service."""
    call_type: str  # "tool", "llm", "function", or "http"
    name: str       # tool or function name, or model name
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InteractionRequest:
        return cls(
            call_type=data.get("call_type", "tool"),
            name=data.get("name", ""),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InteractionResponse:
    """Represents the response returned by a tool or LLM service."""
    output: Any = None
    error: Optional[str] = None
    status: str = "success"  # "success" or "error"
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InteractionResponse:
        return cls(
            output=data.get("output"),
            error=data.get("error"),
            status=data.get("status", "success"),
            duration_ms=float(data.get("duration_ms", 0.0)),
        )


@dataclass
class Interaction:
    """A pair of request and response representing a single recorded turn."""
    request: InteractionRequest
    response: InteractionResponse
    recorded_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Interaction:
        return cls(
            request=InteractionRequest.from_dict(data.get("request", {})),
            response=InteractionResponse.from_dict(data.get("response", {})),
            recorded_at=data.get("recorded_at"),
        )
