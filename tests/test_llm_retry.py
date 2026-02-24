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

