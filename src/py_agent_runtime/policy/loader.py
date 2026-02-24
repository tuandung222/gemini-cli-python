from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.modes import ApprovalMode

import tomllib


@dataclass(frozen=True)
class PolicyLoadResult:
    rules: list[PolicyRule]
    errors: list[str]


def transform_priority(priority: int, tier: int) -> float:
    return tier + priority / 1000


def _iter_policy_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file() and path.suffix == ".toml":
        return [path]
    if path.is_dir():
        return sorted(item for item in path.iterdir() if item.is_file() and item.suffix == ".toml")
    return []


def _as_tool_names(raw_value: Any) -> list[str | None]:
    if raw_value is None:
        return [None]
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        return list(raw_value)
    raise ValueError("toolName must be a string or a list of strings")


def _as_string_list(raw_value: Any, *, field_name: str) -> list[str]:
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        return list(raw_value)
    raise ValueError(f"{field_name} must be a string or a list of strings")


def _build_command_prefix_pattern(prefix: str) -> str:
    escaped = re.escape(prefix)
    return rf"\"command\":\"\s*{escaped}[^\"]*\""


def _build_command_regex_pattern(command_regex: str) -> str:
    return rf"\"command\":\"\s*(?:{command_regex})[^\"]*\""


def load_policies_from_toml(
    policy_paths: Iterable[Path | str],
    get_policy_tier: Callable[[Path], int],
) -> PolicyLoadResult:
    rules: list[PolicyRule] = []
    errors: list[str] = []

    for raw_path in policy_paths:
        path = Path(raw_path)
        for file_path in _iter_policy_files(path):
            try:
                parsed = tomllib.loads(file_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover
                errors.append(f"{file_path}: failed to parse TOML: {exc}")
                continue

            raw_rules = parsed.get("rule", [])
            if not isinstance(raw_rules, list):
                errors.append(f"{file_path}: 'rule' must be an array")
                continue

            tier = get_policy_tier(file_path)
            for index, raw_rule in enumerate(raw_rules):
                try:
                    if not isinstance(raw_rule, dict):
                        raise ValueError("rule must be an object")
                    decision = PolicyDecision(raw_rule["decision"])
                    priority = int(raw_rule["priority"])
                    if priority < 0 or priority > 999:
                        raise ValueError("priority must be in range [0, 999]")

                    modes: list[ApprovalMode] | None = None
                    raw_modes = raw_rule.get("modes")
                    if raw_modes is not None:
                        if not isinstance(raw_modes, list):
                            raise ValueError("modes must be an array")
                        modes = [ApprovalMode(mode) for mode in raw_modes]

                    args_pattern_raw = raw_rule.get("argsPattern")
                    command_prefix_raw = raw_rule.get("commandPrefix")
                    command_regex_raw = raw_rule.get("commandRegex")

                    if command_prefix_raw is not None and command_regex_raw is not None:
                        raise ValueError(
                            "commandPrefix and commandRegex are mutually exclusive"
                        )
                    if args_pattern_raw is not None and (
                        command_prefix_raw is not None or command_regex_raw is not None
                    ):
                        raise ValueError(
                            "argsPattern cannot be combined with commandPrefix/commandRegex"
                        )

                    args_patterns: list[re.Pattern[str] | None] = [None]
                    if isinstance(args_pattern_raw, str):
                        args_patterns = [re.compile(args_pattern_raw)]
                    elif command_prefix_raw is not None:
                        prefixes = _as_string_list(command_prefix_raw, field_name="commandPrefix")
                        args_patterns = [re.compile(_build_command_prefix_pattern(item)) for item in prefixes]
                    elif command_regex_raw is not None:
                        if not isinstance(command_regex_raw, str):
                            raise ValueError("commandRegex must be a string")
                        args_patterns = [re.compile(_build_command_regex_pattern(command_regex_raw))]

                    tool_names = _as_tool_names(raw_rule.get("toolName"))
                    if (command_prefix_raw is not None or command_regex_raw is not None) and (
                        tool_names != ["run_shell_command"]
                    ):
                        raise ValueError(
                            "commandPrefix/commandRegex can only be used with toolName='run_shell_command'"
                        )
                    mcp_name = raw_rule.get("mcpName")
                    allow_redirection = bool(raw_rule.get("allow_redirection", False))
                    deny_message = raw_rule.get("deny_message")
                    source = f"{file_path.name}"

                    for tool_name in tool_names:
                        effective_tool_name: str | None = tool_name
                        if isinstance(mcp_name, str):
                            if tool_name:
                                effective_tool_name = f"{mcp_name}__{tool_name}"
                            else:
                                effective_tool_name = f"{mcp_name}__*"

                        for args_pattern in args_patterns:
                            rules.append(
                                PolicyRule(
                                    tool_name=effective_tool_name,
                                    decision=decision,
                                    priority=transform_priority(priority, tier),
                                    modes=modes,
                                    args_pattern=args_pattern,
                                    allow_redirection=allow_redirection,
                                    deny_message=(
                                        deny_message if isinstance(deny_message, str) else None
                                    ),
                                    source=source,
                                )
                            )
                except Exception as exc:
                    errors.append(f"{file_path}: rule #{index + 1}: {exc}")

    return PolicyLoadResult(rules=rules, errors=errors)
