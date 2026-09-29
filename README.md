# 📼 agent-vcr

**Deterministic Record & Replay for LLM Agent Tool Calls & Completions**

`agent-vcr` makes testing AI agents fast, deterministic, and free from external API costs by intercepting tool calls, database queries, and LLM responses, saving them to readable YAML cassettes, and replaying them in subsequent test runs.

---

## ✨ Features

- 🎯 **Deterministic Agent Testing:** Eliminate flaky agent tests caused by non-deterministic tool outputs or external API latency.
- 🔒 **Automatic Secret Redaction:** Scrubs Bearer tokens, API keys (`sk-...`, `ghp_...`), and passwords automatically before saving cassettes.
- ⚡ **Async & Sync First-Class Support:** Seamlessly wraps synchronous and asynchronous tools.
- 🔌 **Zero-Boilerplate Decorator:** `@record_tool` wraps any Python function or agent tool.
- 🧪 **Pytest Integration:** Built-in `agent_cassette` fixture and `@pytest.mark.agent_vcr` marker.
- 🔄 **Multiple Record Modes:** `once` (default), `none` (replay-only for CI), `all` (re-record), and `new_episodes`.

---

## 📦 Installation

```bash
pip install agent-vcr
```

---

## 🚀 Quickstart

### 1. Basic Usage with `@record_tool` and `use_cassette`

```python
from agent_vcr import use_cassette, record_tool

@record_tool(name="search_web")
def search_web(query: str):
    # Real network call...
    return {"results": [f"Top result for {query}"]}

# First run: Records tool execution to cassette
with use_cassette("cassettes/search_test.yaml"):
    output = search_web("quantum computing")
    print(output)

# Subsequent runs (e.g. in CI): Replays instantly without network calls!
with use_cassette("cassettes/search_test.yaml", record_mode="none"):
    output = search_web("quantum computing")
    print(output)
```

---

### 2. Async Tools

```python
import asyncio
from agent_vcr import use_cassette, record_tool

@record_tool(name="query_database")
async def query_db(user_id: str):
    await asyncio.sleep(1) # Expensive query
    return {"id": user_id, "status": "active"}

async def main():
    async with use_cassette("cassettes/async_db.yaml"):
        user = await query_db("user_42")
        print(user)

asyncio.run(main())
```

---

### 3. Pytest Fixture

```python
import pytest
from agent_vcr import record_tool

@record_tool(name="calculator")
def add(a: int, b: int) -> int:
    return a + b

@pytest.mark.agent_vcr
def test_calculator(agent_cassette):
    result = add(2, 3)
    assert result == 5
```

---

## 🛡️ License

MIT License.
