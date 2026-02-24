from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from py_agent_runtime.agents.llm_runner import LLMAgentRunner
from py_agent_runtime.llm import LLMMessage
from py_agent_runtime.llm.factory import create_provider
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.tools.glob_search import GlobSearchTool
from py_agent_runtime.tools.grep_search import GrepSearchTool
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool
from py_agent_runtime.tools.exit_plan_mode import ExitPlanModeTool
from py_agent_runtime.tools.list_directory import ListDirectoryTool
from py_agent_runtime.tools.read_file import ReadFileTool
from py_agent_runtime.tools.read_todos import ReadTodosTool
from py_agent_runtime.tools.replace import ReplaceTool
from py_agent_runtime.tools.run_shell_command import RunShellCommandTool
from py_agent_runtime.tools.write_file import WriteFileTool
from py_agent_runtime.tools.write_todos import WriteTodosTool
from py_agent_runtime.policy.types import PolicyRule

SUPPORTED_PROVIDERS = ("openai", "gemini", "anthropic", "huggingface")
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-2.5-pro",
    "anthropic": "claude-3-7-sonnet-latest",
    "huggingface": "moonshotai/Kimi-K2.5",
}


def _register_default_tools(config: RuntimeConfig) -> None:
    config.tool_registry.register_tool(GlobSearchTool())
    config.tool_registry.register_tool(GrepSearchTool())
    config.tool_registry.register_tool(ListDirectoryTool())
    config.tool_registry.register_tool(ReadFileTool())
    config.tool_registry.register_tool(ReadTodosTool())
    config.tool_registry.register_tool(ReplaceTool())
    config.tool_registry.register_tool(RunShellCommandTool())
    config.tool_registry.register_tool(WriteFileTool())
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.tool_registry.register_tool(ExitPlanModeTool())
    config.tool_registry.register_tool(WriteTodosTool())


def _default_provider_from_env() -> str:
    raw_value = os.environ.get("PY_AGENT_DEFAULT_PROVIDER", "openai")
    normalized = raw_value.strip().lower()
    if normalized in SUPPORTED_PROVIDERS:
        return normalized
    return "openai"


def _resolve_model(provider: str, model: str | None) -> str:
    explicit = (model or "").strip()
    if explicit:
        return explicit

    env_model = os.environ.get("PY_AGENT_DEFAULT_MODEL", "").strip()
    if env_model:
        return env_model

    return PROVIDER_DEFAULT_MODELS.get(provider.strip().lower(), "gpt-4.1-mini")


def _chat_command(
    prompt: str,
    provider_name: str,
    model: str | None,
    temperature: float | None,
) -> int:
    resolved_model = _resolve_model(provider_name, model)
    provider = create_provider(provider_name, model=resolved_model)
    response = provider.generate(
        messages=[LLMMessage(role="user", content=prompt)],
        temperature=temperature,
    )
    print(response.content or "")
    if response.tool_calls:
        print(json.dumps([call.__dict__ for call in response.tool_calls], ensure_ascii=False, indent=2))
    return 0


def _print_json_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _run_command(args: argparse.Namespace) -> int:
    resolved_model = _resolve_model(args.provider, args.model)
    provider = create_provider(
        args.provider,
        model=resolved_model,
        max_retries=args.max_retries,
        retry_base_delay_seconds=args.retry_base_delay_seconds,
        retry_max_delay_seconds=args.retry_max_delay_seconds,
    )
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=args.plan_enabled,
        approval_mode=ApprovalMode(args.approval_mode),
    )
    _register_default_tools(config)
    completion_schema = _load_completion_schema(args.completion_schema_file)

    runner = LLMAgentRunner(
        config=config,
        provider=provider,
        max_turns=args.max_turns,
        model=resolved_model,
        temperature=args.temperature,
        enable_recovery_turn=not args.disable_recovery_turn,
        completion_schema=completion_schema,
    )
    result = runner.run(user_prompt=args.prompt, system_prompt=args.system_prompt)
    _print_json_payload(
        {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "turns": result.turns,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
        }
    )
    return 0 if result.success else 2


def _mode_command(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=args.plan_enabled,
        approval_mode=ApprovalMode(args.approval_mode),
    )
    _print_json_payload(
        {
            "success": True,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
            "plan_enabled": args.plan_enabled,
            "plans_dir": str(config.plans_dir),
        }
    )
    return 0


def _serialize_policy_rule(rule: PolicyRule) -> dict[str, Any]:
    return {
        "tool_name": rule.tool_name,
        "decision": rule.decision.value,
        "priority": rule.priority,
        "source": rule.source,
        "modes": [mode.value for mode in rule.modes] if rule.modes else [],
        "args_pattern": rule.args_pattern.pattern if rule.args_pattern else None,
    }


def _policies_list_command(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=args.plan_enabled,
        approval_mode=ApprovalMode(args.approval_mode),
    )
    grouped: dict[str, list[dict[str, Any]]] = {
        "default": [],
        "autoEdit": [],
        "yolo": [],
        "plan": [],
    }
    for rule in config.policy_engine.get_rules():
        serialized = _serialize_policy_rule(rule)
        if not rule.modes:
            grouped["default"].append(serialized)
            continue
        for mode in rule.modes:
            grouped.setdefault(mode.value, []).append(serialized)

    _print_json_payload(
        {
            "success": True,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
            "policies": grouped,
        }
    )
    return 0


def _policies_command(args: argparse.Namespace) -> int:
    if args.policies_command == "list":
        return _policies_list_command(args)
    print("Error: missing policies subcommand. Use `policies list`.")
    return 1


def _tools_list_command(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=args.plan_enabled,
        approval_mode=ApprovalMode(args.approval_mode),
    )
    _register_default_tools(config)
    tools = []
    for tool in config.tool_registry.get_all_tools():
        tools.append({"name": tool.name, "description": tool.description})
    tools.sort(key=lambda item: item["name"])
    _print_json_payload(
        {
            "success": True,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
            "tools": tools,
        }
    )
    return 0


def _tools_command(args: argparse.Namespace) -> int:
    if args.tools_command == "list":
        return _tools_list_command(args)
    print("Error: missing tools subcommand. Use `tools list`.")
    return 1


def _plan_enter_command(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=True,
        approval_mode=ApprovalMode.DEFAULT,
    )
    tool = EnterPlanModeTool()
    params: dict[str, Any] = {}
    reason = str(args.reason or "").strip()
    if reason:
        params["reason"] = reason
    result = tool.execute(config=config, params=params)
    _print_json_payload(
        {
            "success": result.error is None,
            "result_display": result.return_display,
            "error": result.error,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
        }
    )
    return 0 if result.error is None else 2


def _plan_exit_command(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).resolve() if args.target_dir else Path.cwd().resolve()
    config = RuntimeConfig(
        target_dir=target_dir,
        interactive=not args.non_interactive,
        plan_enabled=True,
        approval_mode=ApprovalMode.PLAN,
    )
    tool = ExitPlanModeTool()
    params: dict[str, Any] = {
        "plan_path": args.plan_path,
        "approved": not args.rejected,
        "approval_mode": args.approval_mode,
    }
    feedback = args.feedback
    if isinstance(feedback, str) and feedback.strip():
        params["feedback"] = feedback.strip()

    result = tool.execute(config=config, params=params)
    approved_plan_path = config.get_approved_plan_path()
    _print_json_payload(
        {
            "success": result.error is None,
            "result_display": result.return_display,
            "error": result.error,
            "approval_mode": config.get_approval_mode().value,
            "interactive": config.interactive,
            "approved_plan_path": (
                str(approved_plan_path) if approved_plan_path is not None else None
            ),
        }
    )
    return 0 if result.error is None else 2


def _plan_command(args: argparse.Namespace) -> int:
    if args.plan_command == "enter":
        return _plan_enter_command(args)
    if args.plan_command == "exit":
        return _plan_exit_command(args)
    print("Error: missing plan subcommand. Use `plan enter` or `plan exit`.")
    return 1


def _load_completion_schema(schema_file: str | None) -> dict[str, Any] | None:
    if schema_file is None:
        return None
    path = Path(schema_file)
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid completion schema JSON file: {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Invalid completion schema JSON file: {path}: top-level value must be an object."
        )
    return parsed


def main() -> int:
    default_provider = _default_provider_from_env()
    parser = argparse.ArgumentParser(description="py-agent-runtime CLI")
    subparsers = parser.add_subparsers(dest="command")

    chat_parser = subparsers.add_parser("chat", help="Run a basic LLM chat completion.")
    chat_parser.add_argument("--prompt", required=True, help="User prompt.")
    chat_parser.add_argument(
        "--provider",
        default=default_provider,
        choices=list(SUPPORTED_PROVIDERS),
        help="LLM provider backend.",
    )
    chat_parser.add_argument(
        "--model",
        default=None,
        help="Optional model name. If omitted, provider-specific default is used.",
    )
    chat_parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional sampling temperature.",
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Run the provider-driven agent loop with scheduler and tools.",
    )
    run_parser.add_argument("--prompt", required=True, help="User task prompt.")
    run_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )
    run_parser.add_argument("--system-prompt", default=None, help="Optional system prompt.")
    run_parser.add_argument(
        "--provider",
        default=default_provider,
        choices=list(SUPPORTED_PROVIDERS),
        help="LLM provider backend.",
    )
    run_parser.add_argument(
        "--model",
        default=None,
        help="Optional model name. If omitted, provider-specific default is used.",
    )
    run_parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature.")
    run_parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum transient API retries per provider request.",
    )
    run_parser.add_argument(
        "--retry-base-delay-seconds",
        type=float,
        default=0.0,
        help="Base delay in seconds for exponential retry backoff.",
    )
    run_parser.add_argument(
        "--retry-max-delay-seconds",
        type=float,
        default=None,
        help="Optional max delay cap in seconds for exponential retry backoff.",
    )
    run_parser.add_argument("--max-turns", type=int, default=15, help="Maximum tool-call turns.")
    run_parser.add_argument(
        "--approval-mode",
        default=ApprovalMode.DEFAULT.value,
        choices=[mode.value for mode in ApprovalMode],
        help="Approval mode policy.",
    )
    run_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive confirmations (ask_user => deny).",
    )
    run_parser.add_argument(
        "--plan-enabled",
        action="store_true",
        help="Enable Plan Mode directory scaffolding.",
    )
    run_parser.add_argument(
        "--disable-recovery-turn",
        action="store_true",
        help="Disable one final recovery turn when protocol/max-turn limits are hit.",
    )
    run_parser.add_argument(
        "--completion-schema-file",
        default=None,
        help="Optional path to JSON Schema for validating complete_task result output.",
    )
    mode_parser = subparsers.add_parser(
        "mode",
        help="Inspect approval mode and interactive flags for a runtime session.",
    )
    mode_parser.add_argument(
        "--approval-mode",
        default=ApprovalMode.DEFAULT.value,
        choices=[mode.value for mode in ApprovalMode],
        help="Approval mode policy.",
    )
    mode_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive confirmations (ask_user => deny).",
    )
    mode_parser.add_argument(
        "--plan-enabled",
        action="store_true",
        help="Enable Plan Mode directory scaffolding.",
    )
    mode_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )

    plan_parser = subparsers.add_parser("plan", help="Run plan-mode lifecycle helpers.")
    plan_subparsers = plan_parser.add_subparsers(dest="plan_command")
    plan_enter_parser = plan_subparsers.add_parser("enter", help="Enter plan mode.")
    plan_enter_parser.add_argument(
        "--reason",
        default="",
        help="Optional reason displayed in plan-mode message.",
    )
    plan_enter_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive confirmations for this command context.",
    )
    plan_enter_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )

    plan_exit_parser = plan_subparsers.add_parser("exit", help="Exit plan mode with approval.")
    plan_exit_parser.add_argument(
        "--plan-path",
        required=True,
        help="Relative path to a markdown plan under .gemini/tmp/plans.",
    )
    plan_exit_parser.add_argument(
        "--approval-mode",
        default=ApprovalMode.DEFAULT.value,
        choices=[ApprovalMode.DEFAULT.value, ApprovalMode.AUTO_EDIT.value],
        help="Post-plan approval mode.",
    )
    plan_exit_parser.add_argument(
        "--rejected",
        action="store_true",
        help="Reject plan instead of approving it.",
    )
    plan_exit_parser.add_argument(
        "--feedback",
        default=None,
        help="Optional feedback when rejecting a plan.",
    )
    plan_exit_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive confirmations for this command context.",
    )
    plan_exit_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )
    policies_parser = subparsers.add_parser("policies", help="Inspect active policy rules.")
    policies_subparsers = policies_parser.add_subparsers(dest="policies_command")
    policies_list_parser = policies_subparsers.add_parser("list", help="List active policy rules.")
    policies_list_parser.add_argument(
        "--approval-mode",
        default=ApprovalMode.DEFAULT.value,
        choices=[mode.value for mode in ApprovalMode],
        help="Approval mode policy for evaluating mode-specific rules.",
    )
    policies_list_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Evaluate policy engine in non-interactive mode.",
    )
    policies_list_parser.add_argument(
        "--plan-enabled",
        action="store_true",
        help="Enable Plan Mode directory scaffolding.",
    )
    policies_list_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )
    tools_parser = subparsers.add_parser("tools", help="Inspect registered tools.")
    tools_subparsers = tools_parser.add_subparsers(dest="tools_command")
    tools_list_parser = tools_subparsers.add_parser("list", help="List registered tool names.")
    tools_list_parser.add_argument(
        "--approval-mode",
        default=ApprovalMode.DEFAULT.value,
        choices=[mode.value for mode in ApprovalMode],
        help="Approval mode policy for context display.",
    )
    tools_list_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run command context as non-interactive.",
    )
    tools_list_parser.add_argument(
        "--plan-enabled",
        action="store_true",
        help="Enable Plan Mode directory scaffolding.",
    )
    tools_list_parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional target working directory for runtime path confinement.",
    )

    args = parser.parse_args()
    try:
        if args.command == "chat":
            return _chat_command(args.prompt, args.provider, args.model, args.temperature)
        if args.command == "run":
            return _run_command(args)
        if args.command == "mode":
            return _mode_command(args)
        if args.command == "plan":
            return _plan_command(args)
        if args.command == "policies":
            return _policies_command(args)
        if args.command == "tools":
            return _tools_command(args)
    except Exception as exc:
        print(f"Error: {exc}")
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
