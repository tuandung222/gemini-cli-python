from __future__ import annotations

from collections import deque

from py_agent_runtime.scheduler.types import CompletedToolCall, ToolCallRequestInfo


class SchedulerStateManager:
    def __init__(self) -> None:
        self._queue: deque[ToolCallRequestInfo] = deque()
        self._completed: list[CompletedToolCall] = []

    def enqueue(self, requests: list[ToolCallRequestInfo]) -> None:
        self._queue.extend(requests)

    def dequeue(self) -> ToolCallRequestInfo | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def complete(self, call: CompletedToolCall) -> None:
        self._completed.append(call)

    def drain_completed(self) -> list[CompletedToolCall]:
        drained = list(self._completed)
        self._completed.clear()
        return drained
