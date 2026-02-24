from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
RETRYABLE_ERROR_CODES = {
    "rate_limit_exceeded",
    "overloaded_error",
    "timeout",
    "temporarily_unavailable",
}


def call_with_retries(
    fn: Callable[[], T],
    *,
    max_retries: int,
    is_retryable: Callable[[Exception], bool] | None = None,
    base_delay_seconds: float = 0.0,
    max_delay_seconds: float | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if base_delay_seconds < 0:
        raise ValueError("base_delay_seconds must be >= 0")
    if max_delay_seconds is not None and max_delay_seconds < 0:
        raise ValueError("max_delay_seconds must be >= 0")

    checker = is_retryable or is_retryable_exception
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if attempt >= max_retries or not checker(exc):
                raise
            attempt += 1
            delay = _compute_retry_delay(
                retry_attempt=attempt,
                base_delay_seconds=base_delay_seconds,
                max_delay_seconds=max_delay_seconds,
            )
            if delay > 0:
                sleep_fn(delay)


def is_retryable_exception(exc: Exception) -> bool:
    status_code = _extract_status_code(exc)
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    error_code = _extract_error_code(exc)
    if error_code is not None and error_code in RETRYABLE_ERROR_CODES:
        return True
    return False


def _extract_status_code(exc: Exception) -> int | None:
    direct = getattr(exc, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None


def _extract_error_code(exc: Exception) -> str | None:
    direct = getattr(exc, "code", None)
    if isinstance(direct, str):
        return direct

    error = getattr(exc, "error", None)
    nested_code = getattr(error, "code", None)
    if isinstance(nested_code, str):
        return nested_code

    response = getattr(exc, "response", None)
    body = getattr(response, "json", None)
    if callable(body):
        try:
            payload = body()
        except Exception:
            return None
        if isinstance(payload, dict):
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                code = error_obj.get("code")
                if isinstance(code, str):
                    return code
    return None


def _compute_retry_delay(
    *,
    retry_attempt: int,
    base_delay_seconds: float,
    max_delay_seconds: float | None,
) -> float:
    delay: float = float(base_delay_seconds) * (2.0 ** float(retry_attempt - 1))
    if max_delay_seconds is not None and delay > max_delay_seconds:
        return max_delay_seconds
    return delay
