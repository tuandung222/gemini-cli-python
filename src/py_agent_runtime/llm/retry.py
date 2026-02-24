from __future__ import annotations

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
) -> T:
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    checker = is_retryable or is_retryable_exception
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if attempt >= max_retries or not checker(exc):
                raise
            attempt += 1


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
