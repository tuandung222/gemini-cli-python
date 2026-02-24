# Tracing Data Audit (gemini-cli-python)

Date: 2026-02-24
Scope: static code inspection of runtime/tracing-relevant modules.

## Executive verdict

Tracing data quality is **medium for local debugging** but **not good for production observability**.

- Overall score: **4.0/10**
- Decision: **Not yet "good" if requirement is durable, queryable, incident-grade tracing**.

## What is already good

1. Correlation primitives exist in core flow.
- `ToolCallRequestInfo` includes `call_id`, `scheduler_id`, `parent_call_id`, `prompt_id` (`src/py_agent_runtime/scheduler/types.py:23`).
- LLM loop propagates `call_id` and creates turn-level `prompt_id` (`src/py_agent_runtime/agents/llm_runner.py:114`, `src/py_agent_runtime/agents/llm_runner.py:115`).
- Tool response messages return `tool_call_id` back to model (`src/py_agent_runtime/agents/llm_runner.py:130`).

2. Failure classes are structured at scheduler boundary.
- Errors normalized with `error_type` like `invalid_tool_params`, `policy_violation`, `execution_failed`, `unhandled_exception` (`src/py_agent_runtime/scheduler/scheduler.py:64`, `src/py_agent_runtime/scheduler/scheduler.py:84`, `src/py_agent_runtime/scheduler/scheduler.py:131`, `src/py_agent_runtime/scheduler/scheduler.py:155`).

3. Confirmation flow has correlation key.
- Confirmation request/response uses `correlation_id` matching (`src/py_agent_runtime/scheduler/confirmation.py:14`, `src/py_agent_runtime/scheduler/confirmation.py:25`, `src/py_agent_runtime/scheduler/confirmation.py:43`).

## Main gaps (blocking “good tracing data”)

1. No persistent trace sink.
- Message bus is in-memory pub/sub only (`src/py_agent_runtime/bus/message_bus.py:15`).
- Scheduler completion list is in-memory and cleared on drain (`src/py_agent_runtime/scheduler/state_manager.py:25`).
- CLI returns only final summary payload, not per-event trace stream (`src/py_agent_runtime/cli/main.py:90`).

2. Missing timing fields.
- No timestamps, durations, latency metrics in core tracing objects (`src/py_agent_runtime/scheduler/types.py:20`).

3. No logging/telemetry backend integration.
- Codebase has no `logging`/OTel instrumentation in runtime paths (verified by repo search in `src/` and `tests/`).

4. No run/session-level trace identity.
- There is per-tool correlation but no explicit `run_id` spanning full execution lifecycle from user prompt to final answer.

5. No redaction/governance layer for trace payloads.
- Shell tool returns raw `stdout`/`stderr` which can contain secrets (`src/py_agent_runtime/tools/run_shell_command.py:86`).
- No masking policy for prompts/tool args/output before export.

## Scorecard

- Correlation fields: **7/10**
- Failure semantics: **7/10**
- Persisted/queryable traces: **1/10**
- Time/latency observability: **1/10**
- Governance/redaction: **4/10**
- **Overall: 4.0/10**

## Recommended minimum upgrade (MVP)

1. Add `run_id` at agent-run start and propagate to all trace records.
2. Emit append-only JSONL trace records for each event:
- `run_started`, `llm_request`, `llm_response`, `tool_scheduled`, `policy_checked`, `tool_completed`, `run_completed`.
3. Add timing fields on every record:
- `ts`, `duration_ms`, `turn`, `attempt`.
4. Add redaction hook before persistence/export:
- mask keys like `api_key`, `token`, `authorization`, secret-like regex.
5. Add CLI flag `--trace-file` and default `.gemini/traces/<run_id>.jsonl`.

## Quick conclusion

Current architecture has a decent **in-memory control trace**, but does not yet provide **durable operational tracing data**. For production-grade tracing, persistence + timing + run-level identity + redaction are mandatory.
