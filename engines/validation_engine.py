"""
engines/validation_engine.py
─────────────────────────────────────────────────────────────────────────────
Validates user-supplied assumptions against the rules defined in input_schema.json.

Returns a dict of {field_name: error_message}. An empty dict means all values
are valid and the model can proceed to generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engines.project_config import flatten_project_fields, load_input_schema

CONFIG_DIR = Path(__file__).parent.parent / "config"
SCHEMA_PATH = CONFIG_DIR / "input_schema.json"


def load_schema(project_type: str) -> list[dict]:
    """Load the field definitions for a given project type."""
    schema = load_input_schema()
    fields = flatten_project_fields(schema.get(project_type, []))
    if not fields and not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"input_schema.json not found at {SCHEMA_PATH}")
    if not fields:
        raise KeyError(f"No schema defined for project type '{project_type}'")
    return fields


def validate(project_type: str, assumptions: dict[str, Any]) -> dict[str, str]:
    """
    Validate assumptions against schema rules.

    Args:
        project_type: e.g. "Solar Project"
        assumptions:  {"capacity_mw": 100, "ppa_tariff": 4.5, ...}

    Returns:
        Dict of {field_name: error_message} — empty == valid.
    """
    errors: dict[str, str] = {}

    try:
        fields = load_schema(project_type)
    except (FileNotFoundError, KeyError) as exc:
        errors["_schema"] = str(exc)
        return errors

    field_lookup = {f["name"]: f for f in fields}

    for name, value in assumptions.items():
        field = field_lookup.get(name)
        if field is None:
            continue  # ignore extra keys

        label = field.get("label", name)
        ftype = field.get("type", "float")

        # --- Type check ---
        if ftype == "float":
            try:
                value = float(value)
            except (TypeError, ValueError):
                errors[name] = f"{label}: must be a number."
                continue
        elif ftype == "integer":
            try:
                value = int(value)
            except (TypeError, ValueError):
                errors[name] = f"{label}: must be a whole number."
                continue

        # --- Range check ---
        if "min" in field and value < field["min"]:
            errors[name] = (
                f"{label}: value {value} is below minimum {field['min']}."
            )
        elif "max" in field and value > field["max"]:
            errors[name] = (
                f"{label}: value {value} exceeds maximum {field['max']}."
            )

    return errors


def coerce(project_type: str, assumptions: dict[str, Any]) -> dict[str, Any]:
    """
    Return a new assumptions dict with values coerced to their schema types.
    Useful before passing values to the writer engine.
    """
    try:
        fields = load_schema(project_type)
    except (FileNotFoundError, KeyError):
        return assumptions

    coerced = dict(assumptions)
    for field in fields:
        name = field["name"]
        ftype = field.get("type", "float")
        if name in coerced:
            try:
                if ftype == "integer":
                    coerced[name] = int(coerced[name])
                else:
                    coerced[name] = float(coerced[name])
            except (TypeError, ValueError):
                pass  # leave as-is; validate() will catch it

    return coerced
