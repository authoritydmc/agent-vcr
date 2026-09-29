"""Cassette container for loading, matching, recording, and persisting interactions."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import yaml

from agent_vcr.exceptions import (
    CannotOverwriteExistingCassetteError,
    CassetteNotFoundError,
    UnhandledInteractionError,
)
from agent_vcr.matchers import RequestMatcher
from agent_vcr.models import Interaction, InteractionRequest, InteractionResponse, RecordMode
from agent_vcr.sanitizers import Sanitizer


class Cassette:
    """Manages a collection of interactions for a specific test or recording session."""

    def __init__(
        self,
        cassette_path: Union[str, Path],
        record_mode: Union[RecordMode, str] = RecordMode.ONCE,
        sanitizer: Optional[Sanitizer] = None,
        matcher: Optional[RequestMatcher] = None,
        sequential: bool = True,
    ):
        self.path = Path(cassette_path)
        self.record_mode = RecordMode(record_mode) if isinstance(record_mode, str) else record_mode
        self.sanitizer = sanitizer or Sanitizer()
        self.matcher = matcher or RequestMatcher()
        self.sequential = sequential

        self.interactions: List[Interaction] = []
        self.played_indices: Set[int] = set()
        self.is_dirty: bool = False
        self._is_active: bool = False

        self._load()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def file_exists(self) -> bool:
        return self.path.exists()

    def _load(self) -> None:
        """Loads interactions from cassette file if present."""
        if not self.file_exists:
            if self.record_mode == RecordMode.NONE:
                raise CassetteNotFoundError(
                    f"Cassette '{self.path}' not found and record_mode is 'none'."
                )
            self.interactions = []
            return

        if self.record_mode == RecordMode.ALL:
            # Overwrite mode: ignore existing content
            self.interactions = []
            self.is_dirty = True
            return

        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                self.interactions = []
                return

            if self.path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content) or {}
            else:
                data = json.loads(content)

            raw_interactions = data.get("interactions", [])
            self.interactions = [Interaction.from_dict(item) for item in raw_interactions]

    def save(self) -> None:
        """Persists recorded interactions back to file if changes were made or file does not exist."""
        if not self.is_dirty and self.file_exists:
            return

        if self.record_mode == RecordMode.NONE:
            if not self.file_exists:
                raise CassetteNotFoundError(f"Cassette '{self.path}' not found and record_mode is 'none'.")
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "recorded_with": "agent-vcr",
            "interactions": [item.to_dict() for item in self.interactions],
        }

        with open(self.path, "w", encoding="utf-8") as f:
            if self.path.suffix in (".yaml", ".yml"):
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(data, f, indent=2)

        self.is_dirty = False

    def can_record(self) -> bool:
        """Checks if current mode allows recording new calls."""
        if self.record_mode == RecordMode.ALL:
            return True
        if self.record_mode == RecordMode.NEW_EPISODES:
            return True
        if self.record_mode == RecordMode.ONCE and not self.file_exists:
            return True
        return False

    def find_match(self, request: InteractionRequest) -> Optional[InteractionResponse]:
        """Finds a matching interaction from recorded interactions."""
        # Clean request parameters for comparison
        cleaned_request = InteractionRequest(
            call_type=request.call_type,
            name=request.name,
            payload=self.sanitizer.sanitize(request.payload),
            metadata=self.sanitizer.sanitize(request.metadata),
        )

        for i, interaction in enumerate(self.interactions):
            if self.sequential and i in self.played_indices:
                continue

            if self.matcher.matches(cleaned_request, interaction.request):
                self.played_indices.add(i)
                return interaction.response

        return None

    def record(self, request: InteractionRequest, response: InteractionResponse) -> None:
        """Records an interaction after scrubbing sensitive content."""
        if not self.can_record():
            raise CannotOverwriteExistingCassetteError(
                f"Cannot record new interaction on cassette '{self.path}' under mode '{self.record_mode.value}'"
            )

        sanitized_request = InteractionRequest(
            call_type=request.call_type,
            name=request.name,
            payload=self.sanitizer.sanitize(request.payload),
            metadata=self.sanitizer.sanitize(request.metadata),
        )

        sanitized_response = InteractionResponse(
            output=self.sanitizer.sanitize(response.output),
            error=self.sanitizer.sanitize(response.error),
            status=response.status,
            duration_ms=response.duration_ms,
        )

        interaction = Interaction(
            request=sanitized_request,
            response=sanitized_response,
            recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        self.interactions.append(interaction)
        self.is_dirty = True

    def __enter__(self) -> "Cassette":
        self._is_active = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._is_active = False
        self.save()
