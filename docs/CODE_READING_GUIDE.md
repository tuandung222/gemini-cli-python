# Code Reading Guide: Entrypoint, Agent Loop, Orchestration Loop

This guide answers:

1. Entrypoint nằm ở đâu?
2. Agent loop nằm ở đâu?
3. Orchestration loop nằm ở đâu?
4. Nên đọc code theo lộ trình nào để hiểu nhanh nhưng chắc?

## TL;DR (3 files quan trọng nhất)

1. `src/py_agent_runtime/cli/main.py`
- CLI entrypoint runtime (`main()`) và command `run` khởi tạo toàn bộ stack.

2. `src/py_agent_runtime/agents/llm_runner.py`
- Agent loop cấp cao: gọi model, nhận tool calls, dispatch xuống scheduler, thu kết quả, ép `complete_task`.

3. `src/py_agent_runtime/scheduler/scheduler.py`
- Orchestration loop cấp tool-call: validate -> policy check -> ask user/deny/allow -> execute tool -> trả `CompletedToolCall`.

## Entrypoint map

### Package/script entrypoint

- `pyproject.toml` khai báo executable script:
  - `py-agent-runtime = "py_agent_runtime.cli.main:main"` (`pyproject.toml:15`)

### Runtime CLI entrypoint

- Hàm entrypoint thực thi:
  - `main()` (`src/py_agent_runtime/cli/main.py:290`)
- Nhánh chính cho tác vụ agent:
  - command `run` -> `_run_command(...)` (`src/py_agent_runtime/cli/main.py:309`, `src/py_agent_runtime/cli/main.py:62`)
- `_run_command(...)` sẽ:
  - tạo provider (`create_provider`)
  - tạo `RuntimeConfig`
  - register built-in tools
  - tạo `LLMAgentRunner`
  - gọi `runner.run(...)`

## Agent loop nằm ở đâu?

- `LLMAgentRunner.run(...)` (`src/py_agent_runtime/agents/llm_runner.py:52`)

Vòng lặp chính:

1. Build tool schemas + `complete_task` schema (`src/py_agent_runtime/agents/llm_runner.py:59`)
2. Lặp theo turn, gọi model `provider.generate(...)` (`src/py_agent_runtime/agents/llm_runner.py:65`)
3. Parse & validate function calls bằng `LocalAgentExecutor.process_function_calls(...)` (`src/py_agent_runtime/agents/llm_runner.py:96`)
4. Chuyển các tool calls thành `ToolCallRequestInfo` (`src/py_agent_runtime/agents/llm_runner.py:110`)
5. Gọi scheduler để orchestration tools (`src/py_agent_runtime/agents/llm_runner.py:121`)
6. Đưa tool result vào message history role=`tool` (`src/py_agent_runtime/agents/llm_runner.py:127`)
7. Khi có `complete_task`, validate completion schema rồi terminate success (`src/py_agent_runtime/agents/llm_runner.py:144`)

Protocol safety:

- Nếu model không gọi tool / không kết thúc đúng protocol, runner kích hoạt recovery turn (`src/py_agent_runtime/agents/llm_runner.py:221`, `src/py_agent_runtime/agents/llm_runner.py:238`).

## Orchestration loop nằm ở đâu?

- `Scheduler.schedule(...)` (`src/py_agent_runtime/scheduler/scheduler.py:29`)
- Thực thi từng request ở `_process_single_request(...)` (`src/py_agent_runtime/scheduler/scheduler.py:40`)

Pipeline một tool call:

1. Lookup tool registry (`src/py_agent_runtime/scheduler/scheduler.py:42`)
2. Validate params (`src/py_agent_runtime/scheduler/scheduler.py:55`)
3. Policy check (`src/py_agent_runtime/scheduler/scheduler.py:68`)
4. Với `ASK_USER`: gọi confirmation flow (`src/py_agent_runtime/scheduler/scheduler.py:103`)
5. Execute tool (`src/py_agent_runtime/scheduler/scheduler.py:121`)
6. Chuẩn hóa kết quả thành `CompletedToolCall` với status/error_type (`src/py_agent_runtime/scheduler/scheduler.py:134`)

Bridging từ agent loop xuống scheduler:

- `schedule_agent_tools(...)` set `scheduler_id` / `parent_call_id` rồi gọi `Scheduler` (`src/py_agent_runtime/agents/agent_scheduler.py:11`).

## Các file nền tảng cần đọc tiếp

1. Runtime bootstrap:
- `src/py_agent_runtime/runtime/config.py`
- Nạp default policies, message bus, agent registry.

2. Policy engine:
- `src/py_agent_runtime/policy/engine.py`
- Rule matching, non-interactive coercion, shell-redirection safety.

3. Confirmation/message bus:
- `src/py_agent_runtime/scheduler/confirmation.py`
- `src/py_agent_runtime/bus/message_bus.py`

4. Tool protocol guard:
- `src/py_agent_runtime/agents/local_executor.py`
- Contract bắt buộc `complete_task`.

5. Provider abstraction:
- `src/py_agent_runtime/llm/factory.py`
- `src/py_agent_runtime/llm/openai_provider.py`
- `src/py_agent_runtime/llm/normalizer.py`

## Lộ trình đọc mã nguồn đề xuất

## Route A (30-45 phút): hiểu luồng end-to-end

1. `pyproject.toml` (script entrypoint)
2. `src/py_agent_runtime/cli/main.py` (`main`, `_run_command`)
3. `src/py_agent_runtime/runtime/config.py`
4. `src/py_agent_runtime/agents/llm_runner.py`
5. `src/py_agent_runtime/agents/agent_scheduler.py`
6. `src/py_agent_runtime/scheduler/scheduler.py`
7. `src/py_agent_runtime/policy/engine.py`
8. `src/py_agent_runtime/tools/registry.py`

## Route B (90-120 phút): hiểu behavior contracts qua tests

1. `tests/test_llm_runner.py`
- behavior của agent loop, completion schema, recovery turn.

2. `tests/test_scheduler.py`
- policy/confirmation/allow-deny-cancel paths.

3. `tests/test_golden_scenarios.py`
- plan-mode lifecycle + canonical regression scenarios.

4. `tests/test_policy_engine.py`, `tests/test_message_bus.py`
- rule engine semantics và bus-level confirmation flow.

## Route C (deep-dive orchestration)

1. `src/py_agent_runtime/scheduler/types.py`
- canonical request/response models và correlation fields.

2. `src/py_agent_runtime/scheduler/scheduler.py`
- state transition thực tế.

3. `src/py_agent_runtime/scheduler/confirmation.py`
4. `src/py_agent_runtime/bus/message_bus.py`
5. `src/py_agent_runtime/policy/engine.py`
6. `src/py_agent_runtime/policy/defaults/*.toml`

## Call flow (mental model)

`CLI main` -> `RuntimeConfig + tools + provider` -> `LLMAgentRunner.run` -> `provider.generate` -> `FunctionCall list` -> `schedule_agent_tools` -> `Scheduler._process_single_request` -> `policy/confirmation/tool.execute` -> `CompletedToolCall` -> back to `LLMAgentRunner` -> `complete_task` -> final result.

## Practical reading tips

1. Đọc theo “điểm nối” thay vì đọc toàn bộ file:
- `_run_command` -> `LLMAgentRunner.run` -> `schedule_agent_tools` -> `Scheduler._process_single_request`.

2. Luôn song song với test tương ứng:
- đọc một nhánh logic trong code, rồi mở test case cover nhánh đó.

3. Nếu muốn sửa behavior orchestration:
- sửa test trước trong `tests/test_scheduler.py` hoặc `tests/test_llm_runner.py`,
- rồi sửa implementation.
