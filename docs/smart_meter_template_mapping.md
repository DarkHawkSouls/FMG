# Smart Meter Template Mapping

This document describes how Smart Meter Rollout assumptions are mapped to the workbook template at examples/idemo.xlsx.

## Workbook Structure

- Template and generated model preserve the original sheet order and workbook structure.
- The generator writes only to input cells that are numeric constants.
- Formula cells are never overwritten.

## Driver Input Sheets

The Smart Meter template uses these input sheets:

- NTBA
- Capex
- TBA
- Sensitivity

## Logical Assumption Groups

The UI schema is grouped into these sections:

- Model Settings
- Project Scale
- Capex Costs
- Revenue & Billing
- Opex Costs
- Sensitivity
- Financing
- Depreciation & Tax
- Analysis & Risk

## Mapping Rules

- Assumption names are semantic labels (for example: Consumer Meters, Corporate Cost, GST on Capex, Repayment option).
- Cell-address style input names are not used in the schema.
- A single assumption may map to multiple scenario columns where the template expects scenario replication.
- If a target cell contains a formula, the writer skips it and leaves the formula intact.

## Key Module Responsibilities

- engines/project_config.py
  - Loads base and project overlay configs.
  - Normalizes logical sheet names to workbook sheet names.

- engines/assumption_mapper.py
  - Resolves user assumptions to a write map by semantic driver names.

- engines/template_writer.py
  - Copies the template file.
  - Writes values only to allowed sheets.
  - Skips any formula cell.

## Config Files

- config/smart_meter_input_schema.json
  - Grouped schema for Smart Meter Rollout assumptions.

- config/smart_meter_driver_registry.json
  - Semantic driver-to-cell mapping for Smart Meter Rollout.

- config/template_registry.json
  - Smart Meter Rollout points to examples/idemo.xlsx.

## Validation Outcome

The generation pipeline was smoke-tested end-to-end and produced a new workbook under output/generated_models while preserving formulas and workbook structure.
