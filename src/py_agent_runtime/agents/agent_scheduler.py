from __future__ import annotations

from dataclasses import replace

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import CompletedToolCall, ToolCallRequestInfo
from py_agent_runtime.tools.registry import ToolRegistry


def schedule_agent_tools(
    config: RuntimeConfig,
    requests: list[ToolCallRequestInfo],
    scheduler_id: str,
    parent_call_id: str | None = None,
    tool_registry: ToolRegistry | None = None,
) -> list[CompletedToolCall]:
    normalized_requests = [
        replace(request, scheduler_id=scheduler_id, parent_call_id=parent_call_id)
        for request in requests
    ]
    scheduler = Scheduler(config=config, tool_registry=tool_registry)
    return scheduler.schedule(normalized_requests)

