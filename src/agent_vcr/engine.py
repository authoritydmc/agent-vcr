"""Core engine for AgentVCR, providing context management and recording/replay helpers."""

from __future__ import annotations

import functools
import inspect
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from agent_vcr.cassette import Cassette
from agent_vcr.exceptions import AgentVCRError, UnhandledInteractionError
from agent_vcr.matchers import MatcherFunction, RequestMatcher
from agent_vcr.models import InteractionRequest, InteractionResponse, RecordMode
from agent_vcr.sanitizers import Sanitizer

F = TypeVar("F", bound=Callable[..., Any])

_ACTIVE_CASSETTE: Optional[Cassette] = None


def get_active_cassette() -> Optional[Cassette]:
    """Returns the currently active cassette in context, if any."""
    return _ACTIVE_CASSETTE


class use_cassette:
    """Context manager and decorator for scoping interactions to a cassette."""

    def __init__(
        self,
        cassette_path: Union[str, Path],
        record_mode: Union[RecordMode, str] = RecordMode.ONCE,
        sensitive_keys: Optional[List[str]] = None,
        matchers: Optional[List[MatcherFunction]] = None,
        sequential: bool = True,
    ):
        self.path = cassette_path
        self.record_mode = record_mode
        self.sanitizer = Sanitizer(sensitive_keys=sensitive_keys) if sensitive_keys else None
        self.matcher = RequestMatcher(matchers=matchers) if matchers else None
        self.sequential = sequential

        self.cassette = Cassette(
            cassette_path=self.path,
            record_mode=self.record_mode,
            sanitizer=self.sanitizer,
            matcher=self.matcher,
            sequential=self.sequential,
        )
        self._previous_cassette: Optional[Cassette] = None

    def __enter__(self) -> Cassette:
        global _ACTIVE_CASSETTE
        self._previous_cassette = _ACTIVE_CASSETTE
        _ACTIVE_CASSETTE = self.cassette
        self.cassette.__enter__()
        return self.cassette

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global _ACTIVE_CASSETTE
        try:
            self.cassette.__exit__(exc_type, exc_val, exc_tb)
        finally:
            _ACTIVE_CASSETTE = self._previous_cassette

    async def __aenter__(self) -> Cassette:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func: F) -> F:
        """Enables @use_cassette as a decorator on sync and async functions."""
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with self:
                    return await func(*args, **kwargs)
            return async_wrapper  # type: ignore

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)
        return sync_wrapper  # type: ignore


def record_or_replay(
    call_type: str,
    name: str,
    payload: Dict[str, Any],
    execute_fn: Callable[[], Any],
    metadata: Optional[Dict[str, Any]] = None,
    cassette: Optional[Cassette] = None,
) -> Any:
    """
    Executes a function or replays its recorded response if an active cassette is present.
    If no cassette is active, executes the function directly.
    """
    active = cassette or get_active_cassette()
    if not active:
        return execute_fn()

    request = InteractionRequest(
        call_type=call_type,
        name=name,
        payload=payload,
        metadata=metadata or {},
    )

    # 1. Check for recorded match
    matched_response = active.find_match(request)
    if matched_response is not None:
        if matched_response.status == "error":
            raise AgentVCRError(matched_response.error or "Recorded execution error")
        return matched_response.output

    # 2. Check if recording is allowed
    if not active.can_record():
        raise UnhandledInteractionError(f"[{call_type}] {name} with args {payload}")

    # 3. Execute live and record
    start = time.perf_counter()
    status = "success"
    error_msg = None
    output = None

    try:
        output = execute_fn()
        return output
    except Exception as e:
        status = "error"
        error_msg = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        response = InteractionResponse(
            output=output,
            error=error_msg,
            status=status,
            duration_ms=duration_ms,
        )
        active.record(request, response)


async def record_or_replay_async(
    call_type: str,
    name: str,
    payload: Dict[str, Any],
    execute_coro_fn: Callable[[], Any],
    metadata: Optional[Dict[str, Any]] = None,
    cassette: Optional[Cassette] = None,
) -> Any:
    """Async variant of record_or_replay for asynchronous tool/LLM executions."""
    active = cassette or get_active_cassette()
    if not active:
        return await execute_coro_fn()

    request = InteractionRequest(
        call_type=call_type,
        name=name,
        payload=payload,
        metadata=metadata or {},
    )

    matched_response = active.find_match(request)
    if matched_response is not None:
        if matched_response.status == "error":
            raise AgentVCRError(matched_response.error or "Recorded async execution error")
        return matched_response.output

    if not active.can_record():
        raise UnhandledInteractionError(f"[{call_type}] {name} with args {payload}")

    start = time.perf_counter()
    status = "success"
    error_msg = None
    output = None

    try:
        output = await execute_coro_fn()
        return output
    except Exception as e:
        status = "error"
        error_msg = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        response = InteractionResponse(
            output=output,
            error=error_msg,
            status=status,
            duration_ms=duration_ms,
        )
        active.record(request, response)


def record_tool(name: Optional[str] = None, call_type: str = "tool") -> Callable[[F], F]:
    """Decorator to automatically wrap any Python tool function with record/replay support."""
    def decorator(func: F) -> F:
        tool_name = name or func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_tool(*args: Any, **kwargs: Any) -> Any:
                payload = {
                    "args": list(args),
                    "kwargs": kwargs,
                }
                return await record_or_replay_async(
                    call_type=call_type,
                    name=tool_name,
                    payload=payload,
                    execute_coro_fn=lambda: func(*args, **kwargs),
                )
            return async_tool  # type: ignore

        @functools.wraps(func)
        def sync_tool(*args: Any, **kwargs: Any) -> Any:
            payload = {
                "args": list(args),
                "kwargs": kwargs,
            }
            return record_or_replay(
                call_type=call_type,
                name=tool_name,
                payload=payload,
                execute_fn=lambda: func(*args, **kwargs),
            )
        return sync_tool  # type: ignore

    return decorator
