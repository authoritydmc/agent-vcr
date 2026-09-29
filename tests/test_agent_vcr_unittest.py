"""Unittest-compatible test suite for agent-vcr."""

import asyncio
import os
import shutil
import tempfile
import unittest
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


class TestAgentVCR(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sanitizer_redacts_keys_and_patterns(self):
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
        self.assertEqual(sanitized["api_key"], REDACTED_PLACEHOLDER)
        self.assertEqual(sanitized["authorization"], REDACTED_PLACEHOLDER)
        self.assertEqual(sanitized["nested"]["password"], REDACTED_PLACEHOLDER)
        self.assertEqual(sanitized["nested"]["safe_val"], 42)
        self.assertEqual(sanitized["query"], "What is the weather in Paris?")

    def test_basic_record_and_replay(self):
        cassette_path = self.tmp_path / "test_cassette.yaml"
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

        self.assertEqual(res1, {"city": "San Francisco", "temp": 72, "unit": "fahrenheit"})
        self.assertEqual(call_counter["count"], 1)
        self.assertTrue(cassette_path.exists())

        # 2. Second execution: replays from cassette without calling execute_fn
        with use_cassette(cassette_path, record_mode=RecordMode.NONE):
            res2 = record_or_replay(
                call_type="tool",
                name="fetch_weather",
                payload={"city": "San Francisco"},
                execute_fn=lambda: fetch_weather("San Francisco"),
            )

        self.assertEqual(res2, {"city": "San Francisco", "temp": 72, "unit": "fahrenheit"})
        self.assertEqual(call_counter["count"], 1)  # Unchanged! Replayed from cassette!

    def test_record_tool_decorator(self):
        cassette_path = self.tmp_path / "decorator_cassette.yaml"
        eval_count = 0

        @record_tool(name="calculator")
        def calculate(expr: str):
            nonlocal eval_count
            eval_count += 1
            return eval(expr)

        # Record turn
        with use_cassette(cassette_path):
            val1 = calculate("2 + 2")
            val2 = calculate("10 * 5")

        self.assertEqual(val1, 4)
        self.assertEqual(val2, 50)
        self.assertEqual(eval_count, 2)

        # Replay turn (record_mode='none' ensures no real execution allowed)
        with use_cassette(cassette_path, record_mode=RecordMode.NONE):
            replayed1 = calculate("2 + 2")
            replayed2 = calculate("10 * 5")

        self.assertEqual(replayed1, 4)
        self.assertEqual(replayed2, 50)
        self.assertEqual(eval_count, 2)  # No new execution

    def test_unhandled_interaction_in_none_mode(self):
        cassette_path = self.tmp_path / "empty_cassette.yaml"
        with use_cassette(cassette_path, record_mode=RecordMode.ONCE):
            pass

        @record_tool(name="search")
        def search(query: str):
            return [f"result for {query}"]

        with self.assertRaises(UnhandledInteractionError):
            with use_cassette(cassette_path, record_mode=RecordMode.NONE):
                search("new unseen query")

    def test_async_record_and_replay(self):
        async def run_async_test():
            cassette_path = self.tmp_path / "async_cassette.yaml"
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

            self.assertEqual(res1, {"user_id": 101, "name": "User_101"})
            self.assertEqual(async_counter, 1)

            # Replay
            async with use_cassette(cassette_path, record_mode=RecordMode.NONE):
                res2 = await db_query(101)

            self.assertEqual(res2, {"user_id": 101, "name": "User_101"})
            self.assertEqual(async_counter, 1)

        asyncio.run(run_async_test())


if __name__ == "__main__":
    unittest.main()
