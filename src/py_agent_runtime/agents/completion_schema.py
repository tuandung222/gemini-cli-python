from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from typing import Any, Mapping


def validate_completion_output(raw_output: str, schema: Mapping[str, Any]) -> str | None:
    expected_type = schema.get("type")
    value: Any = raw_output

    if expected_type is not None and expected_type != "string":
        try:
            value = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            return (
                "Completion output does not satisfy schema: "
                f"output must be valid JSON for schema type '{expected_type}': {exc}"
            )

    error = _validate_value(value, schema, path="$")
    if error:
        return f"Completion output does not satisfy schema: {error}"
    return None


def _validate_value(value: Any, schema: Mapping[str, Any], path: str) -> str | None:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        return f"{path} must be one of {enum_values!r}"

    schema_type = schema.get("type")
    if schema_type is None:
        return None

    if isinstance(schema_type, list):
        if not schema_type:
            return f"{path} has invalid empty type union"
        errors: list[str] = []
        for type_name in schema_type:
            if not isinstance(type_name, str):
                continue
            candidate = dict(schema)
            candidate["type"] = type_name
            error = _validate_value(value, candidate, path)
            if error is None:
                return None
            errors.append(error)
        if errors:
            return " or ".join(errors)
        return f"{path} has unsupported type union {schema_type!r}"

    if not isinstance(schema_type, str):
        return f"{path} has invalid type declaration"

    if schema_type == "string":
        if not isinstance(value, str):
            return f"{path} must be a string"
        return None

    if schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{path} must be a number"
        return None

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{path} must be an integer"
        return None

    if schema_type == "boolean":
        if not isinstance(value, bool):
            return f"{path} must be a boolean"
        return None

    if schema_type == "null":
        if value is not None:
            return f"{path} must be null"
        return None

    if schema_type == "array":
        if not isinstance(value, list):
            return f"{path} must be an array"
        item_schema = schema.get("items")
        if isinstance(item_schema, MappingABC):
            for idx, item in enumerate(value):
                item_error = _validate_value(item, item_schema, f"{path}[{idx}]")
                if item_error:
                    return item_error
        return None

    if schema_type == "object":
        if not isinstance(value, dict):
            return f"{path} must be an object"

        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    return f"{path}.{key} is required"

        properties = schema.get("properties")
        known_properties: dict[str, Mapping[str, Any]] = {}
        if isinstance(properties, MappingABC):
            for key, item_schema in properties.items():
                if isinstance(key, str) and isinstance(item_schema, MappingABC):
                    known_properties[key] = item_schema

        additional_properties = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_schema = known_properties.get(str(key))
            if child_schema is not None:
                child_error = _validate_value(item, child_schema, f"{path}.{key}")
                if child_error:
                    return child_error
                continue
            if additional_properties is False:
                return f"{path}.{key} is not allowed"
        return None

    return f"{path} has unsupported schema type '{schema_type}'"
