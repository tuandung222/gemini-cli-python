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
- [x] Agent registry dynamic policy baseline (`agents/registry.py`)
- [x] Subagent wrapper + invocation baseline with scheduler integration (`agents/subagent_tool.py`, `agents/agent_scheduler.py`)
- [x] Baseline tests/lint/type-check passing (`pytest`, `ruff`, `mypy`)

## Progress snapshot

- `pytest`: `34 passed`
- `ruff check src tests`: pass
- `mypy src/py_agent_runtime`: pass

Phase-level status (from `docs/PORTING_PLAN.md`):
- Phase 0-1: mostly complete (scope freeze + skeleton/types)
- Phase 2-4: core baseline implemented (policy/scheduler/plan tools), parity hardening still in progress
- Phase 5: in progress (local executor protocol + anti-recursion + dynamic subagent policy + subagent wrapper/invocation baseline)
- Phase 6-8: not started (provider adapters, CLI parity, end-to-end hardening)

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
```

## Next implementation target

Implement next parity milestones:
- harden Phase 5 with richer subagent turn loop semantics and final-warning recovery behavior,
- start Phase 6 provider abstraction (`gemini/openai/anthropic` adapter interface),
- start minimal CLI mode wiring for approval/non-interactive behavior.

## Scope notes

- This port prioritizes orchestration equivalence first.
- Auth/provider-specific integrations are intentionally deferred in MVP.
