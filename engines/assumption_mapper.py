"""
engines/assumption_mapper.py
─────────────────────────────────────────────────────────────────────────────
Maps a flat dict of user assumptions to `{sheet: {cell: value}}` using the
driver_registry.json configuration.

The mapper resolves by matching assumption name (key) against the 'name'
field in each driver entry.  Unrecognised assumption keys are silently
ignored; unmapped driver cells retain their template defaults.
"""

from __future__ import annotations

import json
from typing import Any

from engines.project_config import load_driver_registry


def load_registry() -> dict:
    """Return the full driver registry, including any project overlays."""
    return load_driver_registry()


def _lookup_assumption(name: str, assumptions: dict[str, Any]) -> tuple[str | None, Any | None]:
    """Match by exact key first, then by a normalised label-style key."""
    if name in assumptions:
        return name, assumptions[name]

    normalised = name.replace(" ", "_").replace("-", "_").lower()
    for key, value in assumptions.items():
        key_normalised = str(key).replace(" ", "_").replace("-", "_").lower()
        if key_normalised == normalised:
            return key, value

    return None, None


def map_assumptions(
    project_type: str,
    assumptions: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Resolve user assumptions to a nested write-map.

    Args:
        project_type: e.g. "Solar Project"
        assumptions:  {"capacity_mw": 100, "ppa_tariff": 4.5, ...}

    Returns:
        {
            "NTBA":  {"C8": 100, "C9": 4.5, ...},
            "CAPEX": {"C5": 420, ...},
            "TBA":   {"C5": 0.7, "C6": 0.2517},
        }
    """
    registry = load_registry()

    project_drivers: dict[str, list[dict]] = registry.get(project_type, {})
    if not project_drivers:
        raise KeyError(
            f"No driver registry entry found for project type '{project_type}'. "
            "Run driver_extractor.py or update driver_registry.json."
        )

    write_map: dict[str, dict[str, Any]] = {}

    for sheet_name, driver_list in project_drivers.items():
        write_map[sheet_name] = {}
        for driver in driver_list:
            cell = driver["cell"]
            name = driver["name"]
            _, value = _lookup_assumption(name, assumptions)
            if value is not None:
                write_map[sheet_name][cell] = value

    # Remove sheets where nothing was mapped
    write_map = {k: v for k, v in write_map.items() if v}
    return write_map


def describe_mapping(
    project_type: str,
    assumptions: dict[str, Any],
) -> list[dict]:
    """
    Return a human-readable list of resolved mappings for display purposes.

    Returns:
        [
            {"sheet": "NTBA", "cell": "C8", "name": "capacity_mw", "value": 100},
            ...
        ]
    """
    registry = load_registry()
    project_drivers = registry.get(project_type, {})
    resolved = []

    for sheet_name, driver_list in project_drivers.items():
        for driver in driver_list:
            name = driver["name"]
            _, value = _lookup_assumption(name, assumptions)
            if value is not None:
                resolved.append(
                    {
                        "sheet": sheet_name,
                        "cell":  driver["cell"],
                        "name":  name,
                        "label": driver.get("label", name),
                        "value": value,
                    }
                )

    return resolved
