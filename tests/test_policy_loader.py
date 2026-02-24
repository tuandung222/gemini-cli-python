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

