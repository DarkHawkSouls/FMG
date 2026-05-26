from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add parent directory to path so we can import engines
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engines.project_config import (
    load_input_schema,
    load_driver_registry,
    flatten_project_fields,
)
from engines.validation_engine import validate, coerce
from engines.assumption_mapper import map_assumptions, describe_mapping
from engines.template_writer import write_model
from engines.metrics_extractor import simulate_metrics
from engines.analysis_engine import generate_analysis
from engines.report_generator import generate_pdf_report
from engines.template_scanner import scan_template
from engines.label_detector import detect_labels
from engines.dependency_mapper import map_dependencies

app = FastAPI(
    title="AI Financial Model Platform API",
    description="API backend for AI-assisted financial modeling platform",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Enable CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidatePayload(BaseModel):
    project_type: str
    assumptions: Dict[str, Any]

class GeneratePayload(BaseModel):
    project_type: str
    industry: str
    assumptions: Dict[str, Any]

class AnalyzePayload(BaseModel):
    metrics: Dict[str, Any]
    project_type: str
    industry: str
    assumptions: Dict[str, Any]
    groq_api_key: Optional[str] = None

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/config")
def get_config():
    try:
        # Load registry
        with open(ROOT / "config" / "template_registry.json", encoding="utf-8") as f:
            registry = json.load(f)
        registry.setdefault("Infrastructure", {})["Smart Meter Rollout"] = "examples/idemo.xlsx"

        input_schema = load_input_schema()
        driver_reg = load_driver_registry()

        return {
            "registry": registry,
            "input_schema": input_schema,
            "driver_registry": driver_reg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validate")
def api_validate(payload: ValidatePayload):
    errors = validate(payload.project_type, payload.assumptions)
    return {"errors": errors}

@app.post("/api/generate")
def api_generate(payload: GeneratePayload):
    # Validate first
    errors = validate(payload.project_type, payload.assumptions)
    if errors:
        return {"errors": errors, "success": False}

    # Load registry to find template
    with open(ROOT / "config" / "template_registry.json", encoding="utf-8") as f:
        registry = json.load(f)
    registry.setdefault("Infrastructure", {})["Smart Meter Rollout"] = "examples/idemo.xlsx"

    # Find path
    tmpl_rel = None
    for ind, projs in registry.items():
        if payload.project_type in projs:
            tmpl_rel = projs[payload.project_type]
            break

    if not tmpl_rel:
        raise HTTPException(
            status_code=404, 
            detail=f"Template not registered for project type '{payload.project_type}'"
        )

    tmpl_path = ROOT / tmpl_rel
    if not tmpl_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Template file '{tmpl_rel}' not found on server."
        )

    try:
        coerced_assumptions = coerce(payload.project_type, payload.assumptions)
        write_map = map_assumptions(payload.project_type, coerced_assumptions)
        out_path = write_model(tmpl_path, write_map, payload.project_type, payload.industry)
        
        # Get simulated metrics
        metrics = simulate_metrics(coerced_assumptions, payload.project_type)
        
        # Get description mappings
        mappings = describe_mapping(payload.project_type, coerced_assumptions)

        return {
            "success": True,
            "filename": out_path.name,
            "metrics": metrics,
            "mappings": mappings
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download-model")
def download_model(filename: str = Query(..., description="The generated model filename")):
    # Determine the directory
    if os.environ.get("VERCEL"):
        file_path = Path("/tmp") / filename
    else:
        file_path = ROOT / "output" / "generated_models" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Excel model file not found.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/analyze")
def api_analyze(payload: AnalyzePayload):
    # Inject GROQ_API_KEY if provided
    old_key = os.environ.get("GROQ_API_KEY")
    if payload.groq_api_key:
        os.environ["GROQ_API_KEY"] = payload.groq_api_key
    elif "GROQ_API_KEY" in os.environ:
        # Keep environment variable
        pass

    try:
        memo, source = generate_analysis(
            payload.metrics or {}, 
            payload.project_type, 
            payload.industry, 
            payload.assumptions
        )

        pdf_bytes, pdf_name = generate_pdf_report(
            memo, 
            payload.metrics or {}, 
            payload.project_type, 
            payload.industry
        )

        return {
            "memo": memo,
            "source": source,
            "report_filename": pdf_name
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Restore environment variable
        if old_key:
            os.environ["GROQ_API_KEY"] = old_key
        elif "GROQ_API_KEY" in os.environ and payload.groq_api_key:
            del os.environ["GROQ_API_KEY"]

@app.get("/api/download-report")
def download_report(filename: str = Query(..., description="The generated report filename")):
    # Determine the directory
    if os.environ.get("VERCEL"):
        file_path = Path("/tmp") / filename
    else:
        file_path = ROOT / "output" / "reports" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found.")

    media_type = "application/pdf" if filename.endswith(".pdf") else "text/markdown"
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )

@app.post("/api/scan")
async def api_scan(
    file: UploadFile = File(...),
    driver_sheets: str = Form("NTBA, CAPEX, TBA"),
    industry: str = Form("Custom"),
    project_type: str = Form("Custom Project")
):
    try:
        # Save uploaded file to a temp file
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        driver_sheets_list = [s.strip() for s in driver_sheets.split(",") if s.strip()]

        # Setup paths
        if os.environ.get("VERCEL"):
            session_config = Path("/tmp") / "config" / "sessions" / file.filename.replace(".xlsx", "")
        else:
            session_config = ROOT / "config" / "sessions" / file.filename.replace(".xlsx", "")
        
        session_config.mkdir(parents=True, exist_ok=True)

        # Run scanner pipeline
        scan_result = scan_template(
            tmp_path,
            driver_sheets=driver_sheets_list,
            save_to_config=True,
            config_dir=session_config
        )

        driver_registry_scanned = detect_labels(
            tmp_path,
            driver_candidates=scan_result["driver_candidates"],
            save_to_config=True,
            config_dir=session_config
        )

        dep_map = map_dependencies(
            tmp_path,
            save_to_config=True,
            config_dir=session_config
        )

        # We keep the temp file mapped in a dictionary or we copy it to a persistent place
        # Let's save the template file in session config directory as 'template.xlsx' so we can generate from it later
        saved_template_path = session_config / "template.xlsx"
        shutil.copy2(tmp_path, saved_template_path)

        return {
            "success": True,
            "scan_result": scan_result,
            "driver_registry": driver_registry_scanned,
            "dependency_map": dep_map,
            "session_id": file.filename.replace(".xlsx", ""),
            "industry": industry,
            "project_type": project_type
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-scanned")
def api_generate_scanned(
    session_id: str = Form(...),
    industry: str = Form(...),
    project_type: str = Form(...),
    assumptions_json: str = Form(...)
):
    try:
        assumptions = json.loads(assumptions_json)

        # Resolve paths
        if os.environ.get("VERCEL"):
            session_config = Path("/tmp") / "config" / "sessions" / session_id
        else:
            session_config = ROOT / "config" / "sessions" / session_id

        tmpl_path = session_config / "template.xlsx"
        if not tmpl_path.exists():
            raise HTTPException(status_code=404, detail="Scanned template file not found.")

        # Reconstruct write_map
        write_map: Dict[str, Dict[str, Any]] = {}
        for key_str, val in assumptions.items():
            sheet_name, cell_addr = key_str.split("::", 1)
            if sheet_name not in write_map:
                write_map[sheet_name] = {}
            write_map[sheet_name][cell_addr] = val

        out_path = write_model(tmpl_path, write_map, project_type, industry)

        return {
            "success": True,
            "filename": out_path.name,
            "metrics": None,  # Scanned projects don't have simulated metrics registry
            "mappings": []
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
