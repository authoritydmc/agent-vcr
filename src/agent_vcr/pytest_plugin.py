"""Pytest plugin providing fixtures and markers for agent-vcr."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
import pytest

from agent_vcr.cassette import Cassette
from agent_vcr.engine import use_cassette
from agent_vcr.models import RecordMode


def pytest_configure(config: pytest.Config) -> None:
    """Register custom marker with pytest."""
    config.addinivalue_line(
        "markers",
        "agent_vcr(cassette=None, record_mode='once', ...): Record/replay agent interactions with agent-vcr.",
    )


@pytest.fixture
def agent_cassette(request: pytest.FixtureRequest) -> Generator[Cassette, None, None]:
    """
    Pytest fixture that automatically provisions an agent-vcr cassette.
    Derives the cassette path from test file and test function name by default.
    """
    marker = request.node.get_closest_marker("agent_vcr")
    marker_kwargs = marker.kwargs if marker else {}

    test_file = Path(request.node.fspath)
    cassette_dir = marker_kwargs.get("cassette_dir", test_file.parent / "cassettes")
    cassette_name = marker_kwargs.get("cassette", f"{request.node.name}.yaml")
    record_mode = marker_kwargs.get("record_mode", os.environ.get("AGENT_VCR_RECORD_MODE", RecordMode.ONCE))

    cassette_path = Path(cassette_dir) / cassette_name

    with use_cassette(cassette_path=cassette_path, record_mode=record_mode) as cas:
        yield cas
