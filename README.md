# gemini-cli-python

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-145%20passed-brightgreen)
![Ruff](https://img.shields.io/badge/ruff-all%20checks%20passed-success)
![Mypy](https://img.shields.io/badge/mypy-no%20issues%20found-success)
![Status](https://img.shields.io/badge/status-MVP%20parity%20complete-1f6feb)

Python reimplementation of `gemini-cli` agent runtime with equivalent orchestration logic:
- agent loop
- tool scheduling + confirmation flow
- policy engine (allow/deny/ask)
- planning mode lifecycle
- subagent protocol (`complete_task`)

Authentication-specific features can be simplified or omitted.

## Development workflow

Build and validation follow a parity-first, TDD-oriented process:

1. Select parity target from `docs/PORTING_PLAN.md` and `docs/EQUIVALENCE_MATRIX.md`.
2. Write or extend tests first (unit/golden/e2e boundary) for expected TS-equivalent behavior.
3. Implement the minimal runtime/tool/policy change in `src/py_agent_runtime/`.
4. Run quality gates: `pytest`, `ruff check src tests`, `mypy src/py_agent_runtime`.
5. Update equivalence/docs status only after all gates are green.

## Where to start reading

- Full reading roadmap: `docs/CODE_READING_GUIDE.md`
- Subagent architecture deep dive: `docs/SUBAGENT_TECHNICAL_ARCHITECTURE.md`
- Entrypoint:
  - `pyproject.toml`: script `py-agent-runtime = "py_agent_runtime.cli.main:main"`
  - `src/py_agent_runtime/cli/main.py`: `main()` and `_run_command(...)`
- Agent loop:
  - `src/py_agent_runtime/agents/llm_runner.py`: `LLMAgentRunner.run(...)`
- Orchestration loop:
  - `src/py_agent_runtime/scheduler/scheduler.py`: `Scheduler.schedule(...)` and `_process_single_request(...)`

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
- [x] Core filesystem tools parity baseline (`glob`, `grep_search`, `list_directory`, `read_file`, `write_file`, `replace`, `run_shell_command`)
- [x] Runtime todo-state tools (`write_todos` + `read_todos`) with default allow policies
- [x] Built-in tool parameter JSON Schemas for stronger tool-call structure
- [x] Built-in tool reference documentation (`docs/TOOL_REFERENCE.md`)
- [x] Agent registry dynamic policy baseline (`agents/registry.py`)
- [x] Subagent wrapper + invocation baseline with scheduler integration (`agents/subagent_tool.py`, `agents/agent_scheduler.py`)
- [x] LLM provider core contracts + OpenAI adapter baseline (`llm/base_provider.py`, `llm/openai_provider.py`, `agents/llm_runner.py`)
- [x] Provider factory baseline (`llm/factory.py`) with OpenAI/Gemini/Anthropic/HuggingFace adapters wired
- [x] CLI parity baseline (`cli/main.py`) for `chat`, `run`, `mode`, `plan enter/exit`, `policies list`, `tools list`, retry backoff knobs, and `--target-dir`
- [x] Completion schema enforcement baseline for `complete_task` (`agents/completion_schema.py`, `agents/llm_runner.py`, `agents/subagent_tool.py`)
- [x] Completion schema validator hardening (enum/const/combinators/string-numeric-array constraints)
- [x] Golden/e2e boundary tests for plan/deny/cancellation/non-interactive/recovery (`tests/test_golden_scenarios.py`, `tests/test_llm_runner.py`, `tests/test_message_bus.py`)
- [x] Runtime non-interactive policy coercion baseline (`runtime/config.py`, `policy/engine.py`)
- [x] Provider retry hardening with configurable exponential backoff/cap for transient API errors (`llm/retry.py`)
- [x] Baseline tests/lint/type-check passing (`pytest`, `ruff`, `mypy`)

## Progress snapshot

- Last validated: `2026-02-24`
- `pytest`: `145 passed`
- `ruff check src tests`: pass
- `mypy src/py_agent_runtime`: pass

Phase-level status (from `docs/PORTING_PLAN.md`):
- Phase 0-1: complete
- Phase 2-4: complete
- Phase 5: complete
- Phase 6: complete
- Phase 7: complete
- Phase 8: complete (MVP parity regression suite green)

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

## Provider configuration

Runtime reads OpenAI credentials from environment only:

```bash
export OPENAI_API_KEY="your_key_here"
```

Other provider keys:

```bash
export GEMINI_API_KEY="your_gemini_key_here"      # or GOOGLE_API_KEY
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export HF_TOKEN="your_huggingface_token_here"     # or HUGGINGFACEHUB_API_TOKEN
```

Do not hardcode keys in source, test files, or `.env` committed to git.

Optional defaults for flexible provider/model selection:

```bash
export PY_AGENT_DEFAULT_PROVIDER="huggingface"     # openai|gemini|anthropic|huggingface
export PY_AGENT_DEFAULT_MODEL="moonshotai/Kimi-K2.5"
```

If `--provider` / `--model` are omitted, CLI resolves provider from `PY_AGENT_DEFAULT_PROVIDER`
and model from `PY_AGENT_DEFAULT_MODEL` (or provider-specific fallback).

Key classes for OpenAI flow:
- `src/py_agent_runtime/llm/openai_provider.py`: OpenAI chat-completions adapter
- `src/py_agent_runtime/llm/normalizer.py`: canonical tool-call normalization
- `src/py_agent_runtime/agents/llm_runner.py`: provider -> scheduler -> tool execution loop

Other provider adapters:
- `src/py_agent_runtime/llm/gemini_provider.py`
- `src/py_agent_runtime/llm/anthropic_provider.py`
- `src/py_agent_runtime/llm/huggingface_provider.py`

Quick smoke command (uses OpenAI key from environment):

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main chat --prompt "Say hello from OpenAI adapter"
```

HuggingFace Inference Provider smoke command:

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main chat \
  --provider huggingface \
  --model moonshotai/Kimi-K2.5 \
  --prompt "Say hello from HuggingFace Inference Provider"
```

Agent loop command (provider -> scheduler -> tools):

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main run --prompt "Create a plan and finish with complete_task"
```

Agent loop with provider retry backoff tuning:

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main run \
  --prompt "Implement task with resilient retries" \
  --max-retries 4 \
  --retry-base-delay-seconds 0.2 \
  --retry-max-delay-seconds 1.0
```

Agent loop with completion schema validation:

```bash
cd /Users/admin/TuanDung/repos/gemini-cli-python
.venv/bin/python -m py_agent_runtime.cli.main run \
  --prompt "Return structured summary" \
  --completion-schema-file /absolute/path/to/schema.json
```

## Completion status

MVP parity scope in `docs/PORTING_PLAN.md` is complete.
Deferred scope remains:
- auth/OAuth provider complexity,
- IDE-integration specific UX,
- full extension ecosystem management surface.

## Tracing audit artifacts

- GPT-4 query set for repeatable tracing audits: `docs/tracing/GPT4_TRACING_QUERIES.md`
- Current tracing quality assessment: `docs/tracing/TRACING_AUDIT.md`

## Scope notes

- This port prioritizes orchestration equivalence first.
- Auth/provider-specific integrations are intentionally deferred in MVP.
