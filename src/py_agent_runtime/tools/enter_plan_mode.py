from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult


class EnterPlanModeTool(BaseTool):
    name = "enter_plan_mode"
    description = "Switch to Plan Mode for safe analysis and plan drafting."
    parameters_json_schema = {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        reason = str(params.get("reason", "")).strip()
        config.set_approval_mode(ApprovalMode.PLAN)
        if reason:
            message = f"Switching to Plan mode: {reason}"
        else:
            message = "Switching to Plan mode."
        return ToolResult(llm_content=message, return_display=message)
