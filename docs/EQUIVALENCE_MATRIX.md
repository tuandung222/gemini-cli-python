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
| `packages/core/src/config/config.ts` (plan-relevant parts) | `src/py_agent_runtime/runtime/config.py` | in_progress | Mode + plans_dir + approved path + interactive policy propagation baseline | RT-001 |
| `packages/core/src/agents/local-executor.ts` | `src/py_agent_runtime/agents/local_executor.py` | in_progress | `complete_task` contract + unauthorized guard + allowed-tool filtering (anti-recursion baseline) | AGT-001 |
| `packages/core/src/agents/registry.ts` | `src/py_agent_runtime/agents/registry.py` | in_progress | Dynamic policy registration for local/remote agents implemented | AGT-002 |
| `packages/core/src/agents/subagent-tool-wrapper.ts` | `src/py_agent_runtime/agents/subagent_tool.py` | in_progress | Subagent tool wrapper + local invocation baseline implemented | AGT-003 |
| `packages/core/src/agents/agent-scheduler.ts` | `src/py_agent_runtime/agents/agent_scheduler.py` | in_progress | Agent-scoped scheduling helper implemented | AGT-004 |
| `packages/core/src/confirmation-bus/message-bus.ts` | `src/py_agent_runtime/bus/message_bus.py` | in_progress | Pub/sub + synchronous request/response + policy-aware confirmation handling | BUS-001 |
| `packages/core/src/agents/local-executor.ts` (LLM call loop parts) | `src/py_agent_runtime/agents/llm_runner.py` | in_progress | Provider-driven tool-call loop baseline with scheduler + `complete_task` contract | AGT-005 |
| `packages/core/src/agents/local-executor.ts` (completion contract path) | `src/py_agent_runtime/agents/completion_schema.py` | in_progress | Completion schema validation baseline for final `complete_task` output | AGT-006 |
| `packages/core/src/core/geminiChat.ts` (provider abstraction surface) | `src/py_agent_runtime/llm/base_provider.py` | in_progress | Canonical provider interface for multi-model adapters | LLM-001 |
| `packages/core/src/core/geminiChat.ts` (OpenAI-parity target) | `src/py_agent_runtime/llm/openai_provider.py` | in_progress | OpenAI chat-completions adapter with env key loading | LLM-002 |
| `packages/core/src/core/geminiChat.ts` (Gemini adapter path) | `src/py_agent_runtime/llm/gemini_provider.py` | in_progress | Gemini generate-content adapter baseline with env key loading | LLM-003 |
| `packages/core/src/core/geminiChat.ts` (Anthropic adapter path) | `src/py_agent_runtime/llm/anthropic_provider.py` | in_progress | Anthropic messages adapter baseline with env key loading | LLM-004 |
| `packages/core/src/core/geminiChat.ts` (provider selection path) | `src/py_agent_runtime/llm/factory.py` | in_progress | Provider factory routes `openai`/`gemini`/`anthropic` | LLM-005 |
| `packages/cli/src/config/config.ts` (approval/non-interactive) | `src/py_agent_runtime/cli/main.py` | in_progress | CLI run command wires approval mode + non-interactive + completion schema file baseline | CLI-001 |
| `packages/core/src/agents/local-executor.test.ts` + scheduler/policy e2e paths | `tests/test_golden_scenarios.py` | in_progress | Golden scenario baseline (plan lifecycle, missing plan, policy deny) | E2E-001 |

## Current test mapping

| Test ID | Python test file | Purpose |
|---|---|---|
| POL-001 | `tests/test_policy_engine.py` | Plan precedence + non-interactive coercion |
| POL-002 | `tests/test_policy_loader.py` | Tier transform + array expansion |
| PLN-003 | `tests/test_plan_validation.py` | Path traversal/symlink/content validation |
| SCH-001 | `tests/test_scheduler.py` | Scheduler allow/deny baseline |
| AGT-001 | `tests/test_local_executor.py` | `complete_task` protocol + unauthorized-tool guard + allowed-tool filtering |
| AGT-002 | `tests/test_agent_registry.py` | Dynamic policy behavior for subagent registration |
| AGT-003 | `tests/test_subagent_tool.py` | Subagent invocation, anti-recursion, allowlist, and completion protocol |
| AGT-005 | `tests/test_llm_runner.py` | Provider-driven agent loop with scheduler and complete_task termination |
| AGT-006 | `tests/test_completion_schema.py` | Completion schema validation and error messaging |
| LLM-001 | `tests/test_llm_normalizer.py` | Canonical message/tool-call normalization for OpenAI payloads |
| LLM-002 | `tests/test_openai_provider.py` | OpenAI adapter env key handling and request serialization |
| LLM-003 | `tests/test_gemini_provider.py` | Gemini adapter env key handling and request/response mapping |
| LLM-004 | `tests/test_anthropic_provider.py` | Anthropic adapter env key handling and request/response mapping |
| LLM-005 | `tests/test_llm_factory.py` | Provider factory routing coverage |
| CLI-001 | `tests/test_cli_main.py` | CLI command wiring for chat/run and non-interactive approval mode |
| E2E-001 | `tests/test_golden_scenarios.py` | Golden scenario regression coverage for plan/policy/cancellation flows |
| RT-001 | `tests/test_runtime_config.py` | Runtime interactive mode propagates to policy non-interactive coercion |

## Deferred items

| TS area | Decision |
|---|---|
| OAuth/auth provider complexity | deferred |
| IDE integration specifics | deferred |
| Full extension management surface | deferred |
