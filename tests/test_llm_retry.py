from __future__ import annotations

import pytest

from py_agent_runtime.llm.retry import call_with_retries, is_retryable_exception


class RetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class NonRetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_is_retryable_exception_by_status_code() -> None:
    assert is_retryable_exception(RetryableError("rate limited", 429)) is True
    assert is_retryable_exception(NonRetryableError("bad request", 400)) is False


def test_call_with_retries_retries_then_succeeds() -> None:
    state = {"calls": 0}

    def _fn() -> str:
        state["calls"] += 1
        if state["calls"] < 3:
            raise RetryableError("temporary", 503)
        return "ok"

    result = call_with_retries(_fn, max_retries=2)
    assert result == "ok"
    assert state["calls"] == 3


def test_call_with_retries_stops_on_non_retryable_error() -> None:
    state = {"calls": 0}

    def _fn() -> str:
        state["calls"] += 1
        raise NonRetryableError("bad request", 400)

    with pytest.raises(NonRetryableError):
        call_with_retries(_fn, max_retries=3)
    assert state["calls"] == 1


def test_call_with_retries_supports_exponential_backoff() -> None:
    state = {"calls": 0}
    sleeps: list[float] = []

    def _fn() -> str:
        state["calls"] += 1
        if state["calls"] < 4:
            raise RetryableError("temporary", 503)
        return "ok"

    result = call_with_retries(
        _fn,
        max_retries=3,
        base_delay_seconds=0.1,
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )
    assert result == "ok"
    assert state["calls"] == 4
    assert sleeps == [0.1, 0.2, 0.4]


def test_call_with_retries_caps_backoff_at_max_delay() -> None:
    state = {"calls": 0}
    sleeps: list[float] = []

    def _fn() -> str:
        state["calls"] += 1
        if state["calls"] < 4:
            raise RetryableError("temporary", 503)
        return "ok"

    result = call_with_retries(
        _fn,
        max_retries=3,
        base_delay_seconds=0.1,
        max_delay_seconds=0.15,
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )
    assert result == "ok"
    assert state["calls"] == 4
    assert sleeps == [0.1, 0.15, 0.15]
