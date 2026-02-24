# GPT-4 Tracing Audit Queries

Model target: `gpt-4`

Use each query with the same repository snapshot and ask GPT-4 to return strict JSON so results are comparable.

## Query 1: Event Model Completeness

```text
You are auditing tracing quality for an agent runtime.

Repository: gemini-cli-python
Focus files:
- src/py_agent_runtime/scheduler/types.py
- src/py_agent_runtime/scheduler/scheduler.py
- src/py_agent_runtime/agents/llm_runner.py
- src/py_agent_runtime/bus/message_bus.py
- src/py_agent_runtime/scheduler/confirmation.py

Task:
1) Infer the implicit event model from code.
2) Evaluate whether each event has enough fields for correlation and debugging.
3) Score completeness from 0-10.

Return JSON with schema:
{
  "score": number,
  "event_types": [{"name": string, "required_fields": [string], "missing_fields": [string]}],
  "strengths": [string],
  "gaps": [string],
  "evidence": [{"file": string, "line": number, "claim": string}],
  "top_fixes": [string]
}
```

## Query 2: End-to-End Traceability (LLM -> Tool -> Result)

```text
Audit if one user prompt can be traced end-to-end through the runtime.

Repository: gemini-cli-python
Focus files:
- src/py_agent_runtime/agents/llm_runner.py
- src/py_agent_runtime/llm/normalizer.py
- src/py_agent_runtime/scheduler/scheduler.py
- src/py_agent_runtime/scheduler/types.py
- src/py_agent_runtime/cli/main.py

Questions:
1) Can a single tool call be reconstructed across all stages?
2) Which IDs are present (call_id, prompt_id, scheduler_id, parent_call_id)?
3) Which stages lose context?
4) Is there enough emitted output for production incident analysis?

Return JSON:
{
  "traceability_score": number,
  "available_ids": [string],
  "missing_ids": [string],
  "context_loss_points": [string],
  "prod_readiness": "low|medium|high",
  "evidence": [{"file": string, "line": number, "claim": string}],
  "fix_plan": [string]
}
```

## Query 3: Failure-Path Tracing Quality

```text
Evaluate tracing quality on failure paths.

Repository: gemini-cli-python
Focus files:
- src/py_agent_runtime/scheduler/scheduler.py
- src/py_agent_runtime/agents/llm_runner.py
- src/py_agent_runtime/bus/message_bus.py

Check these failure classes:
- invalid tool params
- policy violation
- user cancellation
- tool execution exception
- model protocol violation (no complete_task)

For each failure class, report:
- whether structured error fields exist
- whether correlation fields are preserved
- whether output is externally observable

Return JSON:
{
  "overall_score": number,
  "failures": [
    {
      "name": string,
      "structured_error": boolean,
      "correlation_preserved": boolean,
      "externally_observable": boolean,
      "evidence": [{"file": string, "line": number, "claim": string}],
      "risk": "low|medium|high"
    }
  ],
  "priority_gaps": [string]
}
```

## Query 4: Telemetry/Storage Readiness

```text
Assess telemetry readiness for production operations.

Repository: gemini-cli-python
Focus files:
- src/py_agent_runtime/bus/message_bus.py
- src/py_agent_runtime/scheduler/state_manager.py
- src/py_agent_runtime/runtime/config.py
- src/py_agent_runtime/cli/main.py

Evaluate:
1) persistent trace sink (file/db/otlp)
2) timestamps/durations
3) queryability (filter by run_id/call_id)
4) metrics export
5) replay capability

Return JSON:
{
  "readiness_score": number,
  "has_persistent_sink": boolean,
  "has_timestamps": boolean,
  "has_metrics_export": boolean,
  "has_replay": boolean,
  "main_blockers": [string],
  "recommended_mvp_schema": {
    "trace_record_fields": [string]
  },
  "evidence": [{"file": string, "line": number, "claim": string}]
}
```

## Query 5: Security and Data Governance in Tracing

```text
Audit tracing safety and governance controls.

Repository: gemini-cli-python
Focus files:
- src/py_agent_runtime/llm/openai_provider.py
- src/py_agent_runtime/agents/llm_runner.py
- src/py_agent_runtime/tools/run_shell_command.py
- src/py_agent_runtime/cli/main.py

Evaluate:
1) risk of leaking secrets in logs/trace payloads
2) redaction support
3) PII handling hooks
4) policy/audit fields needed for compliance

Return JSON:
{
  "governance_score": number,
  "secret_leak_risks": [string],
  "redaction_present": boolean,
  "pii_controls_present": boolean,
  "required_controls": [string],
  "evidence": [{"file": string, "line": number, "claim": string}],
  "minimum_compliance_backlog": [string]
}
```
