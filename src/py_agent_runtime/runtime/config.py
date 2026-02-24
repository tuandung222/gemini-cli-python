from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from py_agent_runtime.bus.message_bus import MessageBus
from py_agent_runtime.policy.engine import PolicyEngine
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.tools.registry import ToolRegistry


@dataclass
class RuntimeConfig:
    target_dir: Path
    interactive: bool = True
    plan_enabled: bool = False
    approval_mode: ApprovalMode = ApprovalMode.DEFAULT
    approved_plan_path: Path | None = None
    policy_engine: PolicyEngine = field(default_factory=PolicyEngine)
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    message_bus: MessageBus = field(init=False)
    plans_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.target_dir = self.target_dir.resolve()
        self.plans_dir = self.target_dir / ".gemini" / "tmp" / "plans"
        if self.plan_enabled:
            self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.policy_engine.set_approval_mode(self.approval_mode)
        self.message_bus = MessageBus(policy_engine=self.policy_engine)

    def set_approval_mode(self, mode: ApprovalMode) -> None:
        self.approval_mode = mode
        self.policy_engine.set_approval_mode(mode)

    def get_approval_mode(self) -> ApprovalMode:
        return self.approval_mode

    def set_approved_plan_path(self, path: Path | None) -> None:
        self.approved_plan_path = path

    def get_approved_plan_path(self) -> Path | None:
        return self.approved_plan_path

    def get_message_bus(self) -> MessageBus:
        return self.message_bus
