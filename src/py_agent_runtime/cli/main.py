from __future__ import annotations

import argparse
import json
from pathlib import Path

from py_agent_runtime.agents.llm_runner import LLMAgentRunner
from py_agent_runtime.llm import LLMMessage
from py_agent_runtime.llm.factory import create_provider
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool
from py_agent_runtime.tools.exit_plan_mode import ExitPlanModeTool
from py_agent_runtime.tools.write_todos import WriteTodosTool


def _register_default_tools(config: RuntimeConfig) -> None:
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.tool_registry.register_tool(ExitPlanModeTool())
    config.tool_registry.register_tool(WriteTodosTool())


def _chat_command(
    prompt: str,
    provider_name: str,
    model: str,
    temperature: float | None,
) -> int:
    provider = create_provider(provider_name, model=model)
    response = provider.generate(
        messages=[LLMMessage(role="user", content=prompt)],
        temperature=temperature,
    )
    print(response.content or "")
    if response.tool_calls:
        print(json.dumps([call.__dict__ for call in response.tool_calls], ensure_ascii=False, indent=2))
    return 0


def _run_command(args: argparse.Namespace) -> int:
    provider = create_provider(args.provider, model=args.model)
    config = RuntimeConfig(
        target_dir=Path.cwd(),
        interactive=not args.non_interactive,
        plan_enabled=args.plan_enabled,
    )
    config.set_approval_mode(ApprovalMode(args.approval_mode))
    _register_default_tools(config)

    runner = LLMAgentRunner(
        config=config,
        provider=provider,
        max_turns=args.max_turns,
        model=args.model,
        temperature=args.temperature,
        enable_recovery_turn=not args.disable_recovery_turn,
    )
    result = runner.run(user_prompt=args.prompt, system_prompt=args.system_prompt)
    print(
        json.dumps(
            {
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "turns": result.turns,
                "approval_mode": config.get_approval_mode().value,
                "interactive": config.interactive,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.success else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="py-agent-runtime CLI")
    subparsers = parser.add_subparsers(dest="command")

    chat_parser = subparsers.add_parser("chat", help="Run a basic LLM chat completion.")
    chat_parser.add_argument("--prompt", required=True, help="User prompt.")
    chat_parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "gemini", "anthropic"],
        help="LLM provider backend.",
    )
    chat_parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
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
    run_parser.add_argument("--system-prompt", default=None, help="Optional system prompt.")
    run_parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "gemini", "anthropic"],
        help="LLM provider backend.",
    )
    run_parser.add_argument("--model", default="gpt-4.1-mini", help="Model name.")
    run_parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature.")
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

    args = parser.parse_args()
    try:
        if args.command == "chat":
            return _chat_command(args.prompt, args.provider, args.model, args.temperature)
        if args.command == "run":
            return _run_command(args)
    except Exception as exc:
        print(f"Error: {exc}")
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
