# gemini-cli-python

Python reimplementation of `gemini-cli` agent runtime with equivalent orchestration logic:
- agent loop
- tool scheduling + confirmation flow
- policy engine (allow/deny/ask)
- planning mode lifecycle
- subagent protocol (`complete_task`)

Authentication-specific features can be simplified or omitted.

## Current status

- [x] Porting workspace created
- [x] Detailed porting roadmap written in `docs/PORTING_PLAN.md`
- [x] Equivalence matrix with test IDs in `docs/EQUIVALENCE_MATRIX.md`
- [x] Python package scaffold under `src/py_agent_runtime/`
- [x] Policy core (`types`, `engine`, `loader`, default TOML policies)
- [x] Plan validation (`plans/validation.py`)
- [x] Core plan tools (`enter_plan_mode`, `exit_plan_mode`, `write_todos`)
- [x] Scheduler confirmation + policy-update loop (`scheduler/*`, `bus/message_bus.py`)
- [x] Runtime auto-load of default policy TOMLs (`policy/defaults_loader.py`, `runtime/config.py`)
- [x] Agent registry dynamic policy baseline (`agents/registry.py`)
- [x] Subagent wrapper + invocation baseline with scheduler integration (`agents/subagent_tool.py`, `agents/agent_scheduler.py`)
- [x] LLM provider core contracts + OpenAI adapter baseline (`llm/base_provider.py`, `llm/openai_provider.py`, `agents/llm_runner.py`)
- [x] Provider factory baseline (`llm/factory.py`) with OpenAI/Gemini/Anthropic adapters wired
- [x] CLI parity baseline (`cli/main.py`) for `chat`, `run`, `mode`, `plan enter/exit`, and retry backoff knobs
- [x] Completion schema enforcement baseline for `complete_task` (`agents/completion_schema.py`, `agents/llm_runner.py`, `agents/subagent_tool.py`)
- [x] Completion schema validator hardening (enum/const/combinators/string-numeric-array constraints)
- [x] Golden/e2e boundary tests for plan/deny/cancellation/non-interactive/recovery (`tests/test_golden_scenarios.py`, `tests/test_llm_runner.py`, `tests/test_message_bus.py`)
- [x] Runtime non-interactive policy coercion baseline (`runtime/config.py`, `policy/engine.py`)
- [x] Provider retry hardening with configurable exponential backoff/cap for transient API errors (`llm/retry.py`)
- [x] Baseline tests/lint/type-check passing (`pytest`, `ruff`, `mypy`)

## Progress snapshot

- `pytest`: `111 passed`
- `ruff check src tests`: pass
- `mypy src/py_agent_runtime`: pass

Phase-level status (from `docs/PORTING_PLAN.md`):
- Phase 0-1: mostly complete (scope freeze + skeleton/types)
- Phase 2-4: core baseline implemented (policy/scheduler/plan tools), parity hardening still in progress
- Phase 5: in progress (local executor protocol + anti-recursion + dynamic subagent policy + subagent wrapper/invocation baseline + recovery turn)
- Phase 6: in progress (provider interface + OpenAI/Gemini/Anthropic adapter baselines + factory)
- Phase 7: mostly complete (CLI chat/run/mode/plan lifecycle + approval mode and non-interactive gates)
- Phase 8: in progress (golden/e2e hardening expanded; further parity stress tests still open)

## Local setup

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
```

## Validation commands

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src/py_agent_runtime
```

## OpenAI configuration

Runtime reads OpenAI credentials from environment only:

```bash
export OPENAI_API_KEY="your_key_here"
```

Other provider keys:

```bash
export GEMINI_API_KEY="your_gemini_key_here"      # or GOOGLE_API_KEY
export ANTHROPIC_API_KEY="your_anthropic_key_here"
```

Do not hardcode keys in source, test files, or `.env` committed to git.

Key classes for OpenAI flow:
- `src/py_agent_runtime/llm/openai_provider.py`: OpenAI chat-completions adapter
- `src/py_agent_runtime/llm/normalizer.py`: canonical tool-call normalization
- `src/py_agent_runtime/agents/llm_runner.py`: provider -> scheduler -> tool execution loop

Other provider adapters:
- `src/py_agent_runtime/llm/gemini_provider.py`
- `src/py_agent_runtime/llm/anthropic_provider.py`

Quick smoke command (uses OpenAI key from environment):

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main chat --prompt "Say hello from OpenAI adapter"
```

Agent loop command (provider -> scheduler -> tools):

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main run --prompt "Create a plan and finish with complete_task"
```

Agent loop with completion schema validation:

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main run \
  --prompt "Return structured summary" \
  --completion-schema-file /absolute/path/to/schema.json
```

## Next implementation target

Implement next parity milestones:
- strengthen provider parity for advanced tool-call edge cases and retry/backoff paths,
- expand Phase 8 golden/e2e scenarios for cancellation/non-interactive/recovery boundary conditions.

## Scope notes

- This port prioritizes orchestration equivalence first.
- Auth/provider-specific integrations are intentionally deferred in MVP.
