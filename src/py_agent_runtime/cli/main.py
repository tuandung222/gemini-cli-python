from __future__ import annotations

import argparse
import json

from py_agent_runtime.llm import LLMMessage, OpenAIChatProvider


def _chat_command(prompt: str, model: str, temperature: float | None) -> int:
    provider = OpenAIChatProvider(model=model)
    response = provider.generate(
        messages=[LLMMessage(role="user", content=prompt)],
        temperature=temperature,
    )
    print(response.content or "")
    if response.tool_calls:
        print(json.dumps([call.__dict__ for call in response.tool_calls], ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="py-agent-runtime CLI")
    subparsers = parser.add_subparsers(dest="command")

    chat_parser = subparsers.add_parser("chat", help="Run a basic OpenAI chat completion.")
    chat_parser.add_argument("--prompt", required=True, help="User prompt.")
    chat_parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
    chat_parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional sampling temperature.",
    )

    args = parser.parse_args()
    if args.command == "chat":
        return _chat_command(args.prompt, args.model, args.temperature)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

