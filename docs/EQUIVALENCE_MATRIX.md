# Equivalence Matrix (TS -> Python)

## How to use

For each TS module, track:
- Python target module.
- Port status (`done`, `in_progress`, `planned`, `deferred`).
- Behavior notes.
- Test ID mapping.

| TS module | Python target | Status | Notes | Test ID |
|---|---|---|---|---|
| `packages/core/src/policy/policy-engine.ts` | `src/py_agent_runtime/policy/engine.py` | in_progress | Priority sorting + `allow/deny/ask_user` + wildcard | POL-001 |
| `packages/core/src/policy/toml-loader.ts` | `src/py_agent_runtime/policy/loader.py` | in_progress | Tier transform (`tier + p/1000`) + TOML rule expansion | POL-002 |
| `packages/core/src/policy/policies/plan.toml` | `src/py_agent_runtime/policy/defaults/plan.toml` | in_progress | Plan catch-all deny + explicit allows | POL-003 |
| `packages/core/src/scheduler/scheduler.ts` | `src/py_agent_runtime/scheduler/scheduler.py` | in_progress | Validate -> policy -> confirmation -> execute pipeline implemented | SCH-001 |
| `packages/core/src/scheduler/state-manager.ts` | `src/py_agent_runtime/scheduler/state_manager.py` | in_progress | Queue + completed tracking baseline | SCH-002 |
| `packages/core/src/scheduler/confirmation.ts` | `src/py_agent_runtime/scheduler/confirmation.py` | in_progress | Correlated confirmation request/response implemented via message bus | SCH-003 |
| `packages/core/src/tools/enter-plan-mode.ts` | `src/py_agent_runtime/tools/enter_plan_mode.py` | in_progress | Mode switch baseline done | PLN-001 |
| `packages/core/src/tools/exit-plan-mode.ts` | `src/py_agent_runtime/tools/exit_plan_mode.py` | in_progress | Validation + mode transition done, approval dialog semantics pending | PLN-002 |
| `packages/core/src/utils/planUtils.ts` | `src/py_agent_runtime/plans/validation.py` | in_progress | Path/content checks including symlink escape tests | PLN-003 |
| `packages/core/src/config/config.ts` (plan-relevant parts) | `src/py_agent_runtime/runtime/config.py` | in_progress | Mode + plans_dir + approved path baseline | RT-001 |
| `packages/core/src/agents/local-executor.ts` | `src/py_agent_runtime/agents/local_executor.py` | in_progress | `complete_task` contract + unauthorized guard + allowed-tool filtering (anti-recursion baseline) | AGT-001 |
| `packages/core/src/agents/registry.ts` | `src/py_agent_runtime/agents/registry.py` | in_progress | Dynamic policy registration for local/remote agents implemented | AGT-002 |
| `packages/core/src/confirmation-bus/message-bus.ts` | `src/py_agent_runtime/bus/message_bus.py` | in_progress | Pub/sub + synchronous request/response + policy-aware confirmation handling | BUS-001 |
| `packages/cli/src/config/config.ts` (approval/non-interactive) | `src/py_agent_runtime/cli/main.py` | planned | CLI mode flags/exclusions pending | CLI-001 |

## Current test mapping

| Test ID | Python test file | Purpose |
|---|---|---|
| POL-001 | `tests/test_policy_engine.py` | Plan precedence + non-interactive coercion |
| POL-002 | `tests/test_policy_loader.py` | Tier transform + array expansion |
| PLN-003 | `tests/test_plan_validation.py` | Path traversal/symlink/content validation |
| SCH-001 | `tests/test_scheduler.py` | Scheduler allow/deny baseline |
| AGT-001 | `tests/test_local_executor.py` | `complete_task` protocol + unauthorized-tool guard + allowed-tool filtering |
| AGT-002 | `tests/test_agent_registry.py` | Dynamic policy behavior for subagent registration |

## Deferred items

| TS area | Decision |
|---|---|
| OAuth/auth provider complexity | deferred |
| IDE integration specifics | deferred |
| Full extension management surface | deferred |
