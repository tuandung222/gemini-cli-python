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


def test_validate_completion_output_string_constraints() -> None:
    success = validate_completion_output(
        "abc",
        {
            "type": "string",
            "minLength": 2,
            "maxLength": 4,
            "pattern": "^[a-z]+$",
        },
    )
    too_short = validate_completion_output(
        "a",
        {
            "type": "string",
            "minLength": 2,
        },
    )
    bad_pattern = validate_completion_output(
        "A1",
        {
            "type": "string",
            "pattern": "^[a-z]+$",
        },
    )
    assert success is None
    assert too_short is not None
    assert "length" in too_short
    assert bad_pattern is not None
    assert "pattern" in bad_pattern


def test_validate_completion_output_array_constraints() -> None:
    success = validate_completion_output(
        "[1,2]",
        {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 3,
            "uniqueItems": True,
        },
    )
    duplicate = validate_completion_output(
        "[1,1]",
        {
            "type": "array",
            "items": {"type": "integer"},
            "uniqueItems": True,
        },
    )
    assert success is None
    assert duplicate is not None
    assert "duplicate" in duplicate.lower()


def test_validate_completion_output_numeric_bounds() -> None:
    success = validate_completion_output(
        '{"score":9}',
        {
            "type": "object",
            "required": ["score"],
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "exclusiveMaximum": 10,
                }
            },
        },
    )
    out_of_range = validate_completion_output(
        '{"score":10}',
        {
            "type": "object",
            "required": ["score"],
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "exclusiveMaximum": 10,
                }
            },
        },
    )
    assert success is None
    assert out_of_range is not None
    assert "exclusive" in out_of_range.lower()


def test_validate_completion_output_one_of_and_const() -> None:
    success = validate_completion_output(
        '{"kind":"summary","summary":"ok"}',
        {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "required": ["kind", "summary"],
                    "properties": {
                        "kind": {"const": "summary"},
                        "summary": {"type": "string"},
                    },
                },
                {
                    "type": "object",
                    "required": ["kind", "score"],
                    "properties": {
                        "kind": {"const": "score"},
                        "score": {"type": "integer"},
                    },
                },
            ],
        },
    )
    invalid = validate_completion_output(
        '{"kind":"summary","summary":"ok","score":1}',
        {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "required": ["kind", "summary"],
                    "properties": {
                        "kind": {"const": "summary"},
                        "summary": {"type": "string"},
                    },
                },
                {
                    "type": "object",
                    "required": ["kind", "score"],
                    "properties": {
                        "kind": {"const": "summary"},
                        "score": {"type": "integer"},
                    },
                },
            ],
        },
    )
    assert success is None
    assert invalid is not None
    assert "oneof" in invalid.lower()
