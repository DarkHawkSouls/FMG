"""
scripts/batch_extract_drivers.py  —  v2
─────────────────────────────────────────────────────────────────────────────
Runs the FULL scanner + label-detection pipeline on every template in
template_registry.json and regenerates driver_registry.json from scratch.

Pipeline per template:
  template_scanner.py  → sheet_structure / formula_registry / driver_candidates
  label_detector.py    → driver_registry  (labels cleaned, units stripped)

Usage:
    python scripts/batch_extract_drivers.py
    python scripts/batch_extract_drivers.py --no-align   # skip schema alignment
    python scripts/batch_extract_drivers.py --show-raw   # also show raw labels
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engines.template_scanner import scan_template
from engines.label_detector   import detect_labels, clean_label

CONFIG_DIR    = ROOT / "config"
REGISTRY_PATH = CONFIG_DIR / "driver_registry.json"


def _align_names_from_seed(
    project_type: str,
    scanned: dict[str, list[dict]],
    seed_registry: dict,
) -> dict[str, list[dict]]:
    """
    Map canonical field names from the seed registry onto the freshly-scanned
    entries by positional order within each sheet.

    Cleans the `label` field (units stripped) but keeps `raw_label`.
    """
    seed_entries = seed_registry.get(project_type, {})

    sheet_field_order: dict[str, list[str]] = {
        sheet: [e["name"] for e in entries]
        for sheet, entries in seed_entries.items()
        if entries and "name" in entries[0]
    }

    aligned: dict[str, list[dict]] = {}
    for sheet_name, cell_list in scanned.items():
        ordered_names = sheet_field_order.get(sheet_name, [])
        new_list = []
        for i, entry in enumerate(cell_list):
            new_entry = dict(entry)
            if i < len(ordered_names):
                new_entry["name"] = ordered_names[i]
            else:
                new_entry.setdefault("name", entry["cell"].lower())
            new_list.append(new_entry)
        aligned[sheet_name] = new_list

    return aligned


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-scan all registered templates and rebuild driver_registry.json."
    )
    parser.add_argument("--no-align",  action="store_true",
                        help="Skip canonical-name alignment (keep raw snake_case names)")
    parser.add_argument("--show-raw",  action="store_true",
                        help="Print raw (un-cleaned) label alongside cleaned label")
    args = parser.parse_args()

    with open(CONFIG_DIR / "template_registry.json", encoding="utf-8") as f:
        template_registry = json.load(f)

    # Load existing registry as alignment seed (has canonical field names)
    seed_registry: dict = {}
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            seed_registry = json.load(f)

    print("=" * 62)
    print("  Batch Driver Extraction v2 — AI Financial Model Platform")
    print("=" * 62)
    print()

    final_registry: dict[str, dict] = {}
    total_projects = 0
    total_cells    = 0
    errors: list   = []

    for industry, projects in template_registry.items():
        print(f"Industry: {industry}")
        print("-" * 42)

        for project_type, rel_path in projects.items():
            tmpl_path = ROOT / rel_path

            if not tmpl_path.exists():
                print(f"  [SKIP] {rel_path} — file not found")
                errors.append((project_type, rel_path, "File not found"))
                continue

            print(f"  Project : {project_type}")
            print(f"  Template: {rel_path}")

            try:
                # ── Step 1: Scan ─────────────────────────────────────
                scan_result = scan_template(
                    tmpl_path,
                    save_to_config=False,   # don't pollute global config/
                )
                candidates = scan_result["driver_candidates"]
                n_cand = sum(len(v) for v in candidates.values())
                print(f"  Candidates detected: {n_cand}")

                # ── Step 2: Label detection ──────────────────────────
                scanned_registry = detect_labels(
                    tmpl_path,
                    driver_candidates=candidates,
                    save_to_config=False,
                )

                # ── Step 3: Align canonical names (optional) ─────────
                if not args.no_align:
                    scanned_registry = _align_names_from_seed(
                        project_type, scanned_registry, seed_registry
                    )

                # ── Print results ────────────────────────────────────
                for sheet_name, entries in scanned_registry.items():
                    if not entries:
                        continue
                    print(f"    {sheet_name}: {len(entries)} drivers")
                    for e in entries:
                        raw_part = (f"  [raw: '{e.get('raw_label','')}']"
                                    if args.show_raw else "")
                        name_part = f"  name='{e.get('name','')}'" if not args.no_align else ""
                        src_tag  = f"[{e.get('source','?')}]"
                        print(f"      {e['cell']:>6}  {src_tag:<8} "
                              f"label='{e['label']}'{name_part}{raw_part}")

                final_registry[project_type] = scanned_registry
                total_cells    += n_cand
                total_projects += 1

            except Exception as exc:
                print(f"  [ERROR] {exc}")
                errors.append((project_type, rel_path, str(exc)))

        print()

    # ── Write merged driver_registry.json ────────────────────────────────
    # Preserve any existing entries for projects not processed this run
    merged = dict(seed_registry)
    merged.update(final_registry)

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print("=" * 62)
    print(f"  Processed : {total_projects} project(s)")
    print(f"  Drivers   : {total_cells} cells registered")
    if errors:
        print(f"  Skipped   : {len(errors)}")
        for pt, path, err in errors:
            print(f"    - {pt}: {err}")
    print(f"  Output    : config/driver_registry.json")
    print("=" * 62)


if __name__ == "__main__":
    main()
