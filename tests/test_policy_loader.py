from pathlib import Path

from py_agent_runtime.policy.loader import load_policies_from_toml


def test_tier_priority_transformation(tmp_path: Path) -> None:
    policy_file = tmp_path / "test.toml"
    policy_file.write_text(
        """
[[rule]]
toolName = "read_file"
decision = "allow"
priority = 70
modes = ["plan"]
""".strip(),
        encoding="utf-8",
    )

    result = load_policies_from_toml([policy_file], lambda _path: 1)
    assert result.errors == []
    assert len(result.rules) == 1
    assert result.rules[0].priority == 1.07


def test_tool_array_expands_rules(tmp_path: Path) -> None:
    policy_file = tmp_path / "array.toml"
    policy_file.write_text(
        """
[[rule]]
toolName = ["glob", "grep_search"]
decision = "allow"
priority = 50
""".strip(),
        encoding="utf-8",
    )

    result = load_policies_from_toml([policy_file], lambda _path: 1)
    assert result.errors == []
    assert sorted(rule.tool_name for rule in result.rules) == ["glob", "grep_search"]


def test_command_prefix_expands_shell_rules(tmp_path: Path) -> None:
    policy_file = tmp_path / "shell_prefix.toml"
    policy_file.write_text(
        """
[[rule]]
toolName = "run_shell_command"
commandPrefix = ["git status", "ls"]
decision = "allow"
priority = 50
""".strip(),
        encoding="utf-8",
    )

    result = load_policies_from_toml([policy_file], lambda _path: 1)
    assert result.errors == []
    assert len(result.rules) == 2
    assert all(rule.args_pattern is not None for rule in result.rules)
    assert any(rule.args_pattern and "git\\ status" in rule.args_pattern.pattern for rule in result.rules)
    assert any(rule.args_pattern and "ls" in rule.args_pattern.pattern for rule in result.rules)


def test_command_prefix_rejects_non_shell_tool(tmp_path: Path) -> None:
    policy_file = tmp_path / "invalid_shell_prefix.toml"
    policy_file.write_text(
        """
[[rule]]
toolName = "read_file"
commandPrefix = "git status"
decision = "allow"
priority = 50
""".strip(),
        encoding="utf-8",
    )

    result = load_policies_from_toml([policy_file], lambda _path: 1)
    assert result.rules == []
    assert len(result.errors) == 1
    assert "commandPrefix/commandRegex can only be used" in result.errors[0]


def test_command_prefix_conflicts_with_args_pattern(tmp_path: Path) -> None:
    policy_file = tmp_path / "shell_conflict.toml"
    policy_file.write_text(
        """
[[rule]]
toolName = "run_shell_command"
commandPrefix = "git status"
argsPattern = "x"
decision = "allow"
priority = 50
""".strip(),
        encoding="utf-8",
    )

    result = load_policies_from_toml([policy_file], lambda _path: 1)
    assert result.rules == []
    assert len(result.errors) == 1
    assert "argsPattern cannot be combined" in result.errors[0]
