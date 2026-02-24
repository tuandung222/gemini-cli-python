from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.plans.validation import validate_plan_content, validate_plan_path
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.tools.base import BaseTool, ToolResult


class ExitPlanModeTool(BaseTool):
    name = "exit_plan_mode"
    description = "Request plan approval and exit Plan Mode."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        plan_path = params.get("plan_path")
        if not isinstance(plan_path, str) or not plan_path.strip():
            return "plan_path is required."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        plan_path = str(params["plan_path"])
        path_error = validate_plan_path(plan_path, config.plans_dir, config.target_dir)
        if path_error:
            return ToolResult(llm_content=path_error, return_display="Error: Invalid plan", error=path_error)

        resolved_plan_path = (config.target_dir / plan_path).resolve(strict=False)
        content_error = validate_plan_content(resolved_plan_path)
        if content_error:
            return ToolResult(
                llm_content=content_error,
                return_display="Error: Invalid plan",
                error=content_error,
            )

        approved = bool(params.get("approved", True))
        if not approved:
            feedback = str(params.get("feedback", "")).strip()
            if feedback:
                text = (
                    f"Plan rejected. User feedback: {feedback}\n\n"
                    f"The plan is stored at: {resolved_plan_path}\n"
                    "Revise the plan based on the feedback."
                )
                return ToolResult(llm_content=text, return_display=f"Feedback: {feedback}")
            text = (
                "Plan rejected. No feedback provided.\n\n"
                f"The plan is stored at: {resolved_plan_path}\n"
                "Ask the user for specific feedback on how to improve the plan."
            )
            return ToolResult(llm_content=text, return_display="Rejected (no feedback)")

        mode_value = params.get("approval_mode", ApprovalMode.DEFAULT.value)
        try:
            new_mode = mode_value if isinstance(mode_value, ApprovalMode) else ApprovalMode(str(mode_value))
        except ValueError:
            new_mode = ApprovalMode.DEFAULT

        if new_mode in {ApprovalMode.PLAN, ApprovalMode.YOLO}:
            text = "Invalid approval_mode for exiting plan mode. Only default or autoEdit are allowed."
            return ToolResult(llm_content=text, return_display="Error", error=text)

        config.set_approval_mode(new_mode)
        config.set_approved_plan_path(resolved_plan_path)

        mode_desc = (
            "Auto-Edit mode (edits will be applied automatically)"
            if new_mode == ApprovalMode.AUTO_EDIT
            else "Default mode (edits will require confirmation)"
        )
        text = (
            f"Plan approved. Switching to {mode_desc}.\n\n"
            f"The approved implementation plan is stored at: {resolved_plan_path}\n"
            "Read and follow the plan strictly during implementation."
        )
        return ToolResult(llm_content=text, return_display=f"Plan approved: {resolved_plan_path}")
