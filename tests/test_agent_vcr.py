"""Comprehensive tests for agent-vcr."""

import asyncio
import os
import pytest
from pathlib import Path

from agent_vcr import (
    RecordMode,
    UnhandledInteractionError,
    record_or_replay,
    record_or_replay_async,
    record_tool,
    use_cassette,
)
from agent_vcr.sanitizers import REDACTED_PLACEHOLDER, Sanitizer


def test_sanitizer_redacts_keys_and_patterns():
    sanitizer = Sanitizer()
    payload = {
        "api_key": "sk-1234567890123456789012345",
        "authorization": "Bearer secret_jwt_token_1234567890",
        "query": "What is the weather in Paris?",
        "nested": {
            "password": "super_secret_password",
            "safe_val": 42,
        },
    }

    sanitized = sanitizer.sanitize(payload)
    assert sanitized["api_key"] == REDACTED_PLACEHOLDER
    assert sanitized["authorization"] == REDACTED_PLACEHOLDER
    assert sanitized["nested"]["password"] == REDACTED_PLACEHOLDER
    assert sanitized["nested"]["safe_val"] == 42
    assert sanitized["query"] == "What is the weather in Paris?"


def test_sanitizer_api_tokens_and_headers():
    sanitizer = Sanitizer()
    text = (
        "OpenAI: sk-proj-abc12345678901234567890 and sk-1234567890123456789012345. "
        "Anthropic: sk-ant-api03-abcdef123456789012345678. "
        "GitHub: ghp_123456789012345678901234567890123456 and gho_123456789012345678901234567890123456. "
        "Slack: xoxb-1234567890-abcdefghij. "
        "Header: Authorization: Bearer secret_bearer_token_123456789 and x-api-key: custom_token_123456789"
    )
    sanitized = sanitizer.sanitize(text)
    assert "sk-proj-" not in sanitized
    assert "sk-ant-" not in sanitized
    assert "ghp_" not in sanitized
    assert "gho_" not in sanitized
    assert "xoxb-" not in sanitized
    assert "secret_bearer_token" not in sanitized
    assert "custom_token" not in sanitized


def test_sanitizer_query_parameters_and_keys():
    sanitizer = Sanitizer()
    url = "https://api.openai.com/v1/chat?api_key=secret_key_12345&foo=bar&token=secret_tok_98765"
    sanitized_url = sanitizer.sanitize(url)
    assert sanitized_url == f"https://api.openai.com/v1/chat?api_key={REDACTED_PLACEHOLDER}&foo=bar&token={REDACTED_PLACEHOLDER}"

    headers = {
        "X-Api-Key": "my-secret-key",
        "Set-Cookie": "session=xyz123",
        "Content-Type": "application/json",
    }
    sanitized_headers = sanitizer.sanitize(headers)
    assert sanitized_headers["X-Api-Key"] == REDACTED_PLACEHOLDER
    assert sanitized_headers["Set-Cookie"] == REDACTED_PLACEHOLDER
    assert sanitized_headers["Content-Type"] == "application/json"



def test_basic_record_and_replay(tmp_path: Path):
    cassette_path = tmp_path / "test_cassette.yaml"
    call_counter = {"count": 0}

    def fetch_weather(city: str) -> dict:
        call_counter["count"] += 1
        return {"city": city, "temp": 72, "unit": "fahrenheit"}

    # 1. First execution: records to cassette
    with use_cassette(cassette_path, record_mode=RecordMode.ONCE):
        res1 = record_or_replay(
            call_type="tool",
            name="fetch_weather",
            payload={"city": "San Francisco"},
            execute_fn=lambda: fetch_weather("San Francisco"),
        )

    assert res1 == {"city": "San Francisco", "temp": 72, "unit": "fahrenheit"}
    assert call_counter["count"] == 1
    assert cassette_path.exists()

    # 2. Second execution: replays from cassette without calling execute_fn
    with use_cassette(cassette_path, record_mode=RecordMode.NONE):
        res2 = record_or_replay(
            call_type="tool",
            name="fetch_weather",
            payload={"city": "San Francisco"},
            execute_fn=lambda: fetch_weather("San Francisco"),
        )

    assert res2 == {"city": "San Francisco", "temp": 72, "unit": "fahrenheit"}
    assert call_counter["count"] == 1  # Unchanged! Replayed from cassette!


def test_record_tool_decorator(tmp_path: Path):
    cassette_path = tmp_path / "decorator_cassette.yaml"
    eval_count = 0

    @record_tool(name="calculator")
    def calculate(expr: str, api_key: str = "secret-123"):
        nonlocal eval_count
        eval_count += 1
        return eval(expr)

    # Record turn
    with use_cassette(cassette_path):
        val1 = calculate("2 + 2")
        val2 = calculate("10 * 5")

    assert val1 == 4
    assert val2 == 50
    assert eval_count == 2

    # Replay turn (record_mode='none' ensures no real execution allowed)
    with use_cassette(cassette_path, record_mode=RecordMode.NONE):
        replayed1 = calculate("2 + 2")
        replayed2 = calculate("10 * 5")

    assert replayed1 == 4
    assert replayed2 == 50
    assert eval_count == 2  # No new execution


def test_unhandled_interaction_in_none_mode(tmp_path: Path):
    cassette_path = tmp_path / "empty_cassette.yaml"
    # Create empty cassette
    with use_cassette(cassette_path, record_mode=RecordMode.ONCE):
        pass

    @record_tool(name="search")
    def search(query: str):
        return [f"result for {query}"]

    with pytest.raises(UnhandledInteractionError):
        with use_cassette(cassette_path, record_mode=RecordMode.NONE):
            search("new unseen query")


@pytest.mark.asyncio
async def test_async_record_and_replay(tmp_path: Path):
    cassette_path = tmp_path / "async_cassette.yaml"
    async_counter = 0

    @record_tool(name="async_database_lookup")
    async def db_query(user_id: int):
        nonlocal async_counter
        async_counter += 1
        await asyncio.sleep(0.01)
        return {"user_id": user_id, "name": f"User_{user_id}"}

    # Record
    async with use_cassette(cassette_path):
        res1 = await db_query(101)

    assert res1 == {"user_id": 101, "name": "User_101"}
    assert async_counter == 1

    # Replay
    async with use_cassette(cassette_path, record_mode=RecordMode.NONE):
        res2 = await db_query(101)

    assert res2 == {"user_id": 101, "name": "User_101"}
    assert async_counter == 1
