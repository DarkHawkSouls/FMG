"""
engines/project_config.py
─────────────────────────────────────────────────────────────────────────────
Shared config loaders for workbook-backed model generation.

This module keeps the base config files intact and allows project-specific
overlays for templates that need a richer schema or a template-specific
driver registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
SMART_METER_SCHEMA_PATH = CONFIG_DIR / "smart_meter_input_schema.json"
SMART_METER_REGISTRY_PATH = CONFIG_DIR / "smart_meter_driver_registry.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_input_schema() -> dict[str, Any]:
    """Load the base input schema and merge any project-specific overlays."""
    schema = _load_json(CONFIG_DIR / "input_schema.json")
    overlay = _load_json(SMART_METER_SCHEMA_PATH)
    schema.update(overlay)
    return schema


def load_driver_registry() -> dict[str, Any]:
    """Load the base driver registry and merge any project-specific overlays."""
    registry = _load_json(CONFIG_DIR / "driver_registry.json")
    overlay = _load_json(SMART_METER_REGISTRY_PATH)
    registry.update(overlay)
    return registry


def flatten_project_fields(project_schema: Any) -> list[dict[str, Any]]:
    """Return a flat list of field definitions from list- or group-based schema."""
    if isinstance(project_schema, list):
        return project_schema

    if isinstance(project_schema, dict):
        flattened: list[dict[str, Any]] = []
        for fields in project_schema.values():
            if isinstance(fields, list):
                flattened.extend(fields)
        return flattened

    return []


def flatten_schema(schema: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Flatten every project definition into a list of field definitions."""
    return {project: flatten_project_fields(fields) for project, fields in schema.items()}


def normalize_sheet_name(sheet_name: str) -> str:
    """Canonicalise workbook sheet names for case-insensitive matching."""
    key = sheet_name.strip().lower()
    if key == "financing":
        return "NTBA"
    if key == "capex":
        return "Capex"
    if key == "ntba":
        return "NTBA"
    if key == "tba":
        return "TBA"
    if key == "sensitivity":
        return "Sensitivity"
    return sheet_name.strip()


def resolve_sheet_name(sheet_names: list[str], desired: str) -> str | None:
    """Resolve a workbook sheet name using case-insensitive matching."""
    target = desired.strip().lower()
    for sheet_name in sheet_names:
        if sheet_name.strip().lower() == target:
            return sheet_name
    return None
