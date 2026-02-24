from __future__ import annotations

from py_agent_runtime.agents.completion_schema import validate_completion_output


def test_validate_completion_output_object_success() -> None:
    error = validate_completion_output(
        '{"summary":"ok","score":1}',
        {
            "type": "object",
            "required": ["summary", "score"],
            "properties": {
                "summary": {"type": "string"},
                "score": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    )
    assert error is None


def test_validate_completion_output_object_rejects_missing_required() -> None:
    error = validate_completion_output(
        '{"summary":"ok"}',
        {
            "type": "object",
            "required": ["summary", "score"],
            "properties": {
                "summary": {"type": "string"},
                "score": {"type": "integer"},
            },
        },
    )
    assert error is not None
    assert "score" in error


def test_validate_completion_output_requires_json_for_object_schema() -> None:
    error = validate_completion_output(
        "plain text",
        {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        },
    )
    assert error is not None
    assert "valid JSON" in error

