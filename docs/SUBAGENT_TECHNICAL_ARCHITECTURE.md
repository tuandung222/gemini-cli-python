# Subagent Support in `py-agent-runtime` (Technical Architecture)

## 1. Executive summary

Short answer: **yes, the Python runtime already has a subagent tool implementation**.

Current support is **real but baseline**:

1. You can define an agent (`AgentDefinition`), register it, wrap it as a tool (`SubagentTool`), and invoke it through the scheduler.
2. The subagent execution path enforces protocol and safety checks (`complete_task`, allowlist, anti-recursion guard).
3. The current design is **not yet a fully autonomous “spawn child LLM agent by prompt” pipeline** in default CLI flow.

## 2. Scope of this document

This document covers:

1. What is implemented today.
2. How subagent execution works end-to-end.
3. Security/policy behavior.
4. Why this is currently a “controlled subagent tool” rather than full dynamic child-agent spawning.
5. Recommended next steps to reach stronger parity for autonomous multi-agent orchestration.

## 3. Code map

Primary files:

1. Subagent tool implementation:
- `src/py_agent_runtime/agents/subagent_tool.py`

2. Agent definition and kind:
- `src/py_agent_runtime/agents/types.py`

3. Agent registry + dynamic policy:
- `src/py_agent_runtime/agents/registry.py`

4. Scheduler bridge used by subagents:
- `src/py_agent_runtime/agents/agent_scheduler.py`
- `src/py_agent_runtime/scheduler/scheduler.py`

5. Root runtime + registries:
- `src/py_agent_runtime/runtime/config.py`

6. Root agent loop:
- `src/py_agent_runtime/agents/llm_runner.py`
- `src/py_agent_runtime/agents/local_executor.py`

## 4. Current subagent model

## 4.1 Data model

`AgentDefinition` (`src/py_agent_runtime/agents/types.py`) includes:

1. `name`, `description`
2. `kind` (`local` / `remote`)
3. `enabled`
4. `tool_names` allowlist for child tool access
5. `completion_schema` for validating final subagent output

## 4.2 Registry behavior

`AgentRegistry.register_agent(...)` (`src/py_agent_runtime/agents/registry.py`) does:

1. Validate basic metadata.
2. Store discovered/enabled definitions.
3. Install dynamic policy for the agent tool name:
- `LOCAL` -> `ALLOW`
- `REMOTE` -> `ASK_USER`

Important: this registry step **does not automatically register the subagent tool object into `ToolRegistry`**. The wrapper must still be built and registered by caller code.

## 4.3 Subagent tool contract

`SubagentTool` (`src/py_agent_runtime/agents/subagent_tool.py`) expects input:

1. `turns`: non-empty array of turns
2. each turn: array of tool calls
3. each tool call: `{name: str, args: object}`

This means subagent execution is currently **scripted turn execution**, not “provide a prompt and let child run its own LLM loop”.

## 5. End-to-end execution flow

## 5.1 Registration flow (manual in code)

Typical flow:

1. Build `RuntimeConfig`
2. Register core tools
3. Create `AgentDefinition`
4. `config.get_agent_registry().register_agent(definition)`
5. `SubagentToolWrapper(definition).build()`
6. `config.tool_registry.register_tool(subagent_tool)`

If step 6 is skipped, the scheduler cannot execute the agent as a tool.

## 5.2 Invocation flow

When a tool call targets subagent name:

1. Scheduler resolves tool by name.
2. `SubagentTool.execute(...)` validates `turns`.
3. Allowed tool set is computed:
- starts from runtime tool registry
- filters by agent allowlist (`tool_names`) if provided
- excludes recursive agent names through `LocalAgentExecutor.build_allowed_tool_names(...)`

4. Each turn:
- parse function calls
- apply local protocol checks
- schedule non-`complete_task` calls via `schedule_agent_tools(...)`
- fail fast on `ERROR` / `CANCELLED`

5. Termination:
- requires `complete_task` contract
- optional `completion_schema` validation for final result

## 5.3 Status/error semantics

Subagent failures are surfaced back through scheduler as tool execution failures with clear messages:

1. protocol errors (`missing complete_task`, malformed calls)
2. unauthorized tool usage
3. child tool execution failures
4. schema violations

## 6. Policy and safety controls

Current controls include:

1. Dynamic per-agent policy injection by registry.
2. Respect for user-authored policy precedence (`ignore_dynamic=True` check).
3. Tool allowlist restriction via `AgentDefinition.tool_names`.
4. Anti-recursion filtering by agent-name exclusion in `build_allowed_tool_names(...)`.
5. Standard scheduler pipeline (validation -> policy -> confirmation -> execution) also applies to child tool calls.

Interpretation:

The subagent mechanism is conservative by default and avoids unrestricted recursive fan-out.

## 7. Test evidence

Dedicated tests in `tests/test_subagent_tool.py` cover:

1. happy-path completion
2. recursive self-call blocking
3. allowlist enforcement
4. missing `complete_task` failure
5. completion schema failure/success

Agent registry dynamic-policy behavior is covered in:

1. `tests/test_agent_registry.py`

## 8. Important limitation: root LLM loop integration

There is a key integration gap for “automatic child-agent spawning from root LLM”:

1. `LLMAgentRunner._build_allowed_tool_names(...)` derives allowed tools using `LocalAgentExecutor.build_allowed_tool_names(...)`.
2. That helper excludes names present in `all_agent_names`.
3. Subagent tool names are exactly agent names.

Practical effect:

In current default design, agent-name tools are filtered from root allowed tool set, so root LLM loop does not naturally expose subagent tools as callable tools without further integration changes.

This is likely intentional for anti-recursion safety in baseline MVP, but it also limits autonomous multi-agent behavior.

## 9. Current capability level

Capability classification:

1. `Implemented`: controlled subagent tool execution path.
2. `Implemented`: policy-aware child tool scheduling.
3. `Implemented`: protocol + schema guardrails.
4. `Not fully implemented`: turnkey “spawn child agent by prompt” experience in CLI runtime.
5. `Not fully implemented`: automatic agent discovery/loading and wiring into default tool surface.

## 10. Recommended roadmap to full child-agent spawning

## 10.1 Integration roadmap (incremental)

1. Add agent loading mechanism (for example from workspace config) at runtime startup.
2. Auto-register `SubagentTool` objects for enabled agent definitions.
3. Introduce a safer recursion guard based on call-chain depth/parent-call graph, not blanket exclusion of all agent names from root tools.
4. Add dedicated root-loop tests where LLM calls subagent tool name and receives child result.
5. Add optional structured params schema to `SubagentTool` for stronger provider tool declarations.

## 10.2 Optional enhancements

1. Add `max_subagent_depth` and `max_subagent_calls` limits.
2. Add per-subagent model/provider overrides.
3. Add trace events for parent/child tool-call lineage.
4. Add CLI commands to list/register/enable/disable agents.

## 11. Usage example (current baseline)

```python
from pathlib import Path
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.agents.types import AgentDefinition, AgentKind
from py_agent_runtime.agents.subagent_tool import SubagentToolWrapper
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import ToolCallRequestInfo

config = RuntimeConfig(target_dir=Path("."), interactive=True)

# Register base tools first (not shown).

definition = AgentDefinition(
    kind=AgentKind.LOCAL,
    name="research_agent",
    description="Research assistant",
    tool_names=("read_file", "grep_search"),
)
config.get_agent_registry().register_agent(definition)

subagent_tool = SubagentToolWrapper(definition).build()
config.tool_registry.register_tool(subagent_tool)

scheduler = Scheduler(config)
result = scheduler.schedule([
    ToolCallRequestInfo(
        name="research_agent",
        args={
            "turns": [
                [{"name": "read_file", "args": {"file_path": "README.md"}}],
                [{"name": "complete_task", "args": {"result": "done"}}],
            ]
        },
    )
])[0]
```

## 12. Final answer to the product question

If the question is:

"Does Python runtime already have subagent tool support (to create child agents)?"

Then the precise answer is:

1. **Yes**, subagent tool machinery exists and is tested.
2. It is currently a **baseline controlled orchestration implementation**.
3. For full autonomous child-agent spawning in default CLI flow, integration work remains.
