# Detailed Porting Plan: TypeScript `gemini-cli` -> Python Agent Runtime

## 1. Goal and constraints

### Main goal

Build a Python agent runtime that behaves like `gemini-cli` in core orchestration semantics, independent of model vendor (Gemini/OpenAI/Anthropic).

### What must be equivalent

1. Agent/tool orchestration loop.
2. Policy decisions (`allow` / `deny` / `ask_user`) with priority rules.
3. Scheduler flow: validation -> policy -> confirmation -> execution -> result.
4. Plan mode lifecycle (`enter_plan_mode` / `exit_plan_mode`) and plan-file constraints.
5. Subagent protocol with mandatory terminal action (`complete_task`).

### What can be simplified initially

1. Authentication, OAuth, provider-specific auth flows.
2. UI parity with Ink/TUI internals.
3. IDE integrations and advanced telemetry backends.

---

## 2. Non-goals (for v1 port)

1. Full parity with every built-in tool at day 1.
2. Full parity with extension ecosystem/MCP server management UX.
3. Full parity with all slash commands.

---

## 3. Proposed Python architecture

Create Python package layout:

```text
gemini-cli-python/
  src/
    py_agent_runtime/
      __init__.py
      runtime/
        config.py
        modes.py
        workspace.py
      policy/
        types.py
        engine.py
        loader.py
        defaults/
          plan.toml
          write.toml
          read_only.toml
          yolo.toml
      bus/
        message_bus.py
        types.py
      scheduler/
        types.py
        state_manager.py
        confirmation.py
        scheduler.py
        policy_bridge.py
      tools/
        base.py
        registry.py
        enter_plan_mode.py
        exit_plan_mode.py
        write_todos.py
        read_file.py
        grep_search.py
        list_directory.py
        write_file.py
        replace.py
      plans/
        validation.py
      agents/
        local_executor.py
        subagent_tool.py
        registry.py
      llm/
        base_provider.py
        gemini_provider.py
        openai_provider.py
        anthropic_provider.py
        normalizer.py
      prompts/
        provider.py
        snippets.py
      cli/
        main.py
        commands.py
        approval_ui.py
  tests/
```

---

## 4. Migration strategy (phased)

## Phase 0: Behavior contract freeze (2-3 days)

### Deliverables

1. `docs/EQUIVALENCE_MATRIX.md` filled with TS source mapping.
2. List of invariants to preserve.
3. Acceptance test scenarios for parity.

### Tasks

1. Extract canonical flows from TS:
   - plan mode transitions,
   - scheduler state transitions,
   - policy precedence,
   - subagent completion behavior.
2. Write expected I/O traces (input event -> policy -> outcome).
3. Freeze initial scope for MVP.

### Exit criteria

1. You can answer: “Equivalent means exactly what?” in unambiguous terms.

---

## Phase 1: Core skeleton + type system (2-3 days)

### Deliverables

1. Python package scaffolding.
2. Core enums/dataclasses:
   - `ApprovalMode`,
   - `PolicyDecision`,
   - `CoreToolCallStatus`,
   - tool call request/response types.
3. Basic logging setup.

### Tasks

1. Set Python version target: 3.11+.
2. Add dependency stack:
   - `pydantic` (or dataclasses + attrs),
   - `typer` for CLI,
   - `rich` for console UX,
   - `pytest` + `pytest-asyncio`.
3. Setup strict lint/type:
   - `ruff`,
   - `mypy`.

### Exit criteria

1. Skeleton imports cleanly.
2. Type-checked core contracts exist.

---

## Phase 2: Policy engine parity (4-6 days)

### Deliverables

1. `policy.engine` with deterministic priority sorting.
2. TOML loader with tier transformation.
3. Plan policy defaults.

### Tasks

1. Implement rule matching:
   - tool name,
   - wildcard MCP-like names,
   - args regex.
2. Implement tier transform equivalent to TS (`tier + p/1000`).
3. Implement non-interactive coercion (`ask_user -> deny`).
4. Port deny-message behavior.

### Exit criteria

1. Policy regression tests for key scenarios pass:
   - plan deny overrides subagent dynamic allow,
   - explicit plan allows still work,
   - non-interactive conversion works.

---

## Phase 3: Message bus + scheduler state machine (5-7 days)

### Deliverables

1. `MessageBus` with correlation IDs.
2. `SchedulerStateManager` and transition-safe updates.
3. `Scheduler` orchestration pipeline.

### Tasks

1. Implement message types:
   - confirmation request/response,
   - update policy,
   - tool calls update,
   - ask-user request/response.
2. Implement scheduler queueing + cancellation.
3. Implement protocol flow:
   - validate,
   - check policy,
   - confirmation loop,
   - policy update,
   - execute.

### Exit criteria

1. Deterministic state transitions tested.
2. Correlated confirmation round trip tested.

---

## Phase 4: Tooling baseline + plan mode tools (4-6 days)

### Deliverables

1. Core tool framework (`BaseTool`, invocation, registry).
2. Plan tools:
   - `enter_plan_mode`,
   - `exit_plan_mode`.
3. Plan file validation module.

### Tasks

1. Implement synchronous param guard + async deep validation for plan path.
2. Enforce plans directory confinement and non-empty plan checks.
3. Implement mode switching side effects:
   - tool surface sync,
   - approved plan path binding.

### Exit criteria

1. Plan mode lifecycle tests pass, including reject/cancel branches.

---

## Phase 5: Agent loop + subagent protocol (5-8 days)

### Deliverables

1. Local agent executor loop.
2. `complete_task` mandatory terminal protocol.
3. Subagent tool wrapper and anti-recursion filtering.

### Tasks

1. Build per-turn model call + tool execution cycle.
2. Require `complete_task` to finalize.
3. Add grace-turn recovery on timeout/max-turn/protocol violation.
4. Ensure subagent tools filtered from self-recursive availability.

### Exit criteria

1. Protocol violation and recovery tests pass.
2. Completion schema validation enforced.

---

## Phase 6: Multi-model abstraction (Gemini/OpenAI/Anthropic) (5-8 days)

### Deliverables

1. Unified provider interface.
2. Tool-call normalization layer.
3. 3 provider adapters.

### Tasks

1. Define canonical internal event format:
   - thought/content chunks,
   - tool call requests,
   - finish/error events.
2. Map provider-specific tool-call structures into canonical format.
3. Add provider-specific retry/error mapping.

### Exit criteria

1. Same scheduler/tool stack runs unchanged across providers.

---

## Phase 7: CLI UX + non-interactive mode (3-5 days)

### Deliverables

1. CLI command runner.
2. Approval mode indicator/cycle.
3. Non-interactive behavior gates.

### Tasks

1. Implement commands:
   - `/plan`,
   - mode switches.
2. Implement auto-approve behavior for `YOLO` / `AUTO_EDIT` only.
3. Ensure non-interactive excludes prompt-required tools.

### Exit criteria

1. CLI parity tests for approval-mode behavior pass.

---

## Phase 8: Hardening + parity regression suite (5-7 days)

### Deliverables

1. End-to-end parity scenarios.
2. Failure-mode tests.
3. Documentation for extension points.

### Tasks

1. Golden scenario tests:
   - planning directive,
   - inquiry without plan file,
   - policy denial paths,
   - subagent completion protocol.
2. Stress cancellation/timeouts.
3. Add fixtures for multi-provider responses.

### Exit criteria

1. MVP “behaviorally equivalent” checklist is green.

---

## 5. Equivalence checklist (must pass)

1. Plan mode blocks non-whitelisted modifications.
2. Exit plan mode requires valid, confined, non-empty plan file.
3. Policy precedence math deterministic and tested.
4. Scheduler never executes denied call.
5. Confirmation correlation is lossless.
6. Subagent cannot recursively call itself.
7. Agent cannot finish without `complete_task`.

---

## 6. Suggested implementation order (high ROI)

1. Policy engine.
2. Scheduler + message bus.
3. Plan mode tools.
4. Agent loop + complete_task.
5. Provider adapters.

Reason: this order builds safety/governance core first, then model backends become pluggable details.

---

## 7. Estimated timeline

For one strong engineer working focused:

1. MVP parity core (Phase 0-5): ~4-6 weeks.
2. Multi-provider + CLI polish (Phase 6-8): +2-4 weeks.

Total realistic: ~6-10 weeks.

---

## 8. Risks and mitigations

1. Risk: Provider tool-call semantics diverge.
   - Mitigation: strict normalization layer + adapter tests.
2. Risk: Hidden TS behavior in edge cases.
   - Mitigation: parity tests derived from TS test corpus.
3. Risk: Priority bugs causing unsafe allows.
   - Mitigation: lock invariants with regression tests first.

---

## 9. Immediate next steps (today)

1. Approve package name + directory (`gemini-cli-python`).
2. Approve MVP scope (Phase 0-5) and defer auth.
3. Start Phase 0 by filling `docs/EQUIVALENCE_MATRIX.md` from actual TS modules.

