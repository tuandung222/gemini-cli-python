from __future__ import annotations

import json
import re
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
    if "const" in schema and value != schema.get("const"):
        return f"{path} must equal {schema.get('const')!r}"

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        return f"{path} must be one of {enum_values!r}"

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for item_schema in all_of:
            if isinstance(item_schema, MappingABC):
                item_error = _validate_value(value, item_schema, path)
                if item_error:
                    return item_error

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        matched = False
        for item_schema in any_of:
            if not isinstance(item_schema, MappingABC):
                continue
            if _validate_value(value, item_schema, path) is None:
                matched = True
                break
        if not matched:
            return f"{path} must match at least one schema in anyOf"

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        match_count = 0
        for item_schema in one_of:
            if not isinstance(item_schema, MappingABC):
                continue
            if _validate_value(value, item_schema, path) is None:
                match_count += 1
        if match_count != 1:
            return f"{path} must match exactly one schema in oneOf (matched {match_count})"

    not_schema = schema.get("not")
    if isinstance(not_schema, MappingABC):
        if _validate_value(value, not_schema, path) is None:
            return f"{path} must not match schema in not"

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
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            return f"{path} length must be >= {min_length}"
        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            return f"{path} length must be <= {max_length}"
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            try:
                if re.search(pattern, value) is None:
                    return f"{path} must match pattern {pattern!r}"
            except re.error:
                return f"{path} has invalid regex pattern {pattern!r}"
        return None

    if schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{path} must be a number"
        numeric_error = _validate_numeric_constraints(float(value), schema, path)
        if numeric_error:
            return numeric_error
        return None

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{path} must be an integer"
        numeric_error = _validate_numeric_constraints(float(value), schema, path)
        if numeric_error:
            return numeric_error
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
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            return f"{path} must have at least {min_items} items"
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            return f"{path} must have at most {max_items} items"
        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            for item in value:
                serialized = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
                if serialized in seen:
                    return f"{path} must not contain duplicate items"
                seen.add(serialized)

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

        min_properties = schema.get("minProperties")
        if isinstance(min_properties, int) and len(value) < min_properties:
            return f"{path} must have at least {min_properties} properties"
        max_properties = schema.get("maxProperties")
        if isinstance(max_properties, int) and len(value) > max_properties:
            return f"{path} must have at most {max_properties} properties"

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
            if isinstance(additional_properties, MappingABC):
                child_error = _validate_value(item, additional_properties, f"{path}.{key}")
                if child_error:
                    return child_error
        return None

    return f"{path} has unsupported schema type '{schema_type}'"


def _validate_numeric_constraints(
    value: float,
    schema: Mapping[str, Any],
    path: str,
) -> str | None:
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and value < float(minimum):
        return f"{path} must be >= {minimum}"

    maximum = schema.get("maximum")
    if isinstance(maximum, (int, float)) and value > float(maximum):
        return f"{path} must be <= {maximum}"

    exclusive_minimum = schema.get("exclusiveMinimum")
    if isinstance(exclusive_minimum, (int, float)) and value <= float(exclusive_minimum):
        return f"{path} must be > {exclusive_minimum} (exclusiveMinimum)"

    exclusive_maximum = schema.get("exclusiveMaximum")
    if isinstance(exclusive_maximum, (int, float)) and value >= float(exclusive_maximum):
        return f"{path} must be < {exclusive_maximum} (exclusiveMaximum)"

    multiple_of = schema.get("multipleOf")
    if isinstance(multiple_of, (int, float)) and multiple_of > 0:
        quotient = value / float(multiple_of)
        if abs(round(quotient) - quotient) > 1e-9:
            return f"{path} must be a multiple of {multiple_of}"
    return None
