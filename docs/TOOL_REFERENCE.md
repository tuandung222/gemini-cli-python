# Tool Reference

This document summarizes built-in tools currently registered by the CLI runtime.

## Filesystem tools

### `list_directory`
- Purpose: list files/folders under a path inside target directory.
- Params:
  - `path` (string, optional, default `"."`)
- Notes:
  - Denies path escape outside target directory.

### `read_file`
- Purpose: read UTF-8 file content.
- Params:
  - `file_path` (string, required)
- Notes:
  - Denies path escape outside target directory.

### `write_file`
- Purpose: write UTF-8 content to file.
- Params:
  - `file_path` (string, required)
  - `content` (string, required)
- Notes:
  - Creates parent directories automatically.
  - Denies path escape outside target directory.

### `replace`
- Purpose: replace text in a UTF-8 file.
- Params:
  - `file_path` (string, required)
  - `old_text` (string, required, non-empty)
  - `new_text` (string, required)
  - `replace_all` (boolean, optional, default `true`)
- Notes:
  - Errors if `old_text` is not found.
  - Denies path escape outside target directory.

### `glob`
- Purpose: find path matches with glob pattern.
- Params:
  - `pattern` (string, required)
  - `path` (string, optional, default `"."`)

### `grep_search`
- Purpose: search content across files.
- Params:
  - `query` (string, required)
  - `path` (string, optional, default `"."`)
  - `file_pattern` (string, optional, default `"**/*"`)
  - `max_results` (integer, optional, default `100`)
  - `case_sensitive` (boolean, optional, default `false`)
  - `use_regex` (boolean, optional, default `false`)

## Planning tools

### `enter_plan_mode`
- Purpose: switch runtime approval mode to `plan`.
- Params:
  - `reason` (string, optional)

### `exit_plan_mode`
- Purpose: validate and approve/reject plan file, then switch out of plan mode.
- Params:
  - `plan_path` (string, required)
  - `approved` (boolean, optional, default `true`)
  - `approval_mode` (string, optional, default `default`; supports `default`, `autoEdit`)
  - `feedback` (string, optional)

## Task management tools

### `write_todos`
- Purpose: replace todo list payload with validated statuses.
- Params:
  - `todos` (array, required)
  - each item:
    - `description` (string)
    - `status` (`pending` | `in_progress` | `completed` | `cancelled`)

## Runtime CLI commands

- `chat`
- `run`
- `mode`
- `plan enter`
- `plan exit`
- `policies list`
