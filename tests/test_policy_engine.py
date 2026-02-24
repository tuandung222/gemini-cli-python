from py_agent_runtime.policy.engine import PolicyEngine
from py_agent_runtime.policy.types import PolicyCheckInput, PolicyDecision, PolicyRule
from py_agent_runtime.runtime.modes import ApprovalMode


def test_plan_deny_overrides_subagent_allow() -> None:
    engine = PolicyEngine(
        rules=[
            PolicyRule(
                decision=PolicyDecision.DENY,
                priority=1.06,
                modes=[ApprovalMode.PLAN],
            ),
            PolicyRule(
                tool_name="codebase_investigator",
                decision=PolicyDecision.ALLOW,
                priority=1.05,
            ),
        ],
        approval_mode=ApprovalMode.PLAN,
    )

    result = engine.check(PolicyCheckInput(name="codebase_investigator"))
    assert result.decision == PolicyDecision.DENY


def test_explicit_allow_wins_over_plan_catch_all() -> None:
    engine = PolicyEngine(
        rules=[
            PolicyRule(
                decision=PolicyDecision.DENY,
                priority=1.06,
                modes=[ApprovalMode.PLAN],
            ),
            PolicyRule(
                tool_name="read_file",
                decision=PolicyDecision.ALLOW,
                priority=1.07,
                modes=[ApprovalMode.PLAN],
            ),
        ],
        approval_mode=ApprovalMode.PLAN,
    )

    result = engine.check(PolicyCheckInput(name="read_file"))
    assert result.decision == PolicyDecision.ALLOW


def test_non_interactive_converts_ask_user_to_deny() -> None:
    engine = PolicyEngine(
        rules=[PolicyRule(tool_name="ask_user", decision=PolicyDecision.ASK_USER, priority=1.0)],
        non_interactive=True,
    )

    result = engine.check(PolicyCheckInput(name="ask_user"))
    assert result.decision == PolicyDecision.DENY


def test_shell_redirection_downgrades_allow_to_ask_user() -> None:
    engine = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="run_shell_command",
                decision=PolicyDecision.ALLOW,
                priority=2.0,
            )
        ],
        approval_mode=ApprovalMode.DEFAULT,
    )

    result = engine.check(
        PolicyCheckInput(name="run_shell_command", args={"command": "echo hi > out.txt"})
    )
    assert result.decision == PolicyDecision.ASK_USER


def test_shell_redirection_keeps_allow_in_auto_edit_mode() -> None:
    engine = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="run_shell_command",
                decision=PolicyDecision.ALLOW,
                priority=2.0,
            )
        ],
        approval_mode=ApprovalMode.AUTO_EDIT,
    )

    result = engine.check(
        PolicyCheckInput(name="run_shell_command", args={"command": "echo hi > out.txt"})
    )
    assert result.decision == PolicyDecision.ALLOW


def test_shell_redirection_respects_allow_redirection_rule() -> None:
    engine = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="run_shell_command",
                decision=PolicyDecision.ALLOW,
                priority=2.0,
                allow_redirection=True,
            )
        ],
        approval_mode=ApprovalMode.DEFAULT,
    )

    result = engine.check(
        PolicyCheckInput(name="run_shell_command", args={"command": "echo hi > out.txt"})
    )
    assert result.decision == PolicyDecision.ALLOW
