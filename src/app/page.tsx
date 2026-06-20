"use client";

import { useState, useEffect } from "react";

interface Field {
  name: string;
  label: string;
  type: string;
  min: number;
  max: number;
  default: number;
  unit?: string;
}

interface Registry {
  [industry: string]: {
    [project: string]: string;
  };
}

interface InputSchema {
  [project: string]: Field[] | { [group: string]: Field[] };
}

interface ScanSummary {
  sheet_count: number;
  total_formula_cells: number;
  total_numeric_cells: number;
  total_driver_candidates: number;
}

interface SheetStructure {
  classification: string;
  formula_cell_count: number;
  numeric_cell_count: number;
  is_driver_sheet: boolean;
}

interface ScanResult {
  sheet_count: number;
  sheet_structure: {
    [sheetName: string]: SheetStructure;
  };
  summary: ScanSummary;
}

interface DriverEntry {
  cell: string;
  label: string;
  raw_label: string;
  value: number;
  source: string;
}

interface DriverRegistry {
  [sheetName: string]: DriverEntry[];
}

interface DependencyMap {
  [sheetName: string]: string[];
}

export default function Home() {
  // Navigation & Keys
  const [activeTab, setActiveTab] = useState<"curated" | "upload">("curated");
  const [groqKey, setGroqKey] = useState<string>("");

  // Metadata / Configuration
  const [registry, setRegistry] = useState<Registry>({});
  const [inputSchema, setInputSchema] = useState<InputSchema>({});
  const [loadingConfig, setLoadingConfig] = useState<boolean>(true);
  const [configError, setConfigError] = useState<string | null>(null);

  // Tab 1: Curated Templates State
  const [t1Industry, setT1Industry] = useState<string>("");
  const [t1Project, setT1Project] = useState<string>("");
  const [t1Assumptions, setT1Assumptions] = useState<{ [key: string]: number }>({});
  const [t1ValidationErrors, setT1ValidationErrors] = useState<{ [key: string]: string }>({});
  const [t1Generating, setT1Generating] = useState<boolean>(false);
  const [t1GenResult, setT1GenResult] = useState<{
    filename: string;
    metrics: any;
    mappings: any[];
  } | null>(null);
  const [t1Analyzing, setT1Analyzing] = useState<boolean>(false);
  const [t1AnalysisResult, setT1AnalysisResult] = useState<{
    memo: string;
    source: string;
    report_filename: string;
  } | null>(null);

  // Tab 2: Upload Template State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [t2DriverSheets, setT2DriverSheets] = useState<string>("NTBA, CAPEX, TBA");
  const [t2Industry, setT2Industry] = useState<string>("Custom");
  const [t2Project, setT2Project] = useState<string>("Custom Project");
  const [scanning, setScanning] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<{
    success: boolean;
    scan_result: ScanResult;
    driver_registry: DriverRegistry;
    dependency_map: DependencyMap;
    session_id: string;
    industry: string;
    project_type: string;
  } | null>(null);
  const [t2Assumptions, setT2Assumptions] = useState<{ [key: string]: number }>({});
  const [t2Generating, setT2Generating] = useState<boolean>(false);
  const [t2GenResult, setT2GenResult] = useState<{
    filename: string;
  } | null>(null);

  // Load configuration from FastAPI
  useEffect(() => {
    fetch("/api/config")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load platform configuration.");
        return res.json();
      })
      .then((data) => {
        setRegistry(data.registry || {});
        setInputSchema(data.input_schema || {});
        
        // Auto-select first industry & project if available
        const industries = Object.keys(data.registry || {});
        if (industries.length > 0) {
          const defaultInd = industries[0];
          setT1Industry(defaultInd);
          const projects = Object.keys(data.registry[defaultInd] || {});
          if (projects.length > 0) {
            setT1Project(projects[0]);
          }
        }
        setLoadingConfig(false);
      })
      .catch((err) => {
        console.error(err);
        setConfigError(err.message);
        setLoadingConfig(false);
      });
  }, []);

  // Sync Tab 1 default assumptions when project type changes
  useEffect(() => {
    if (!t1Project || !inputSchema[t1Project]) return;
    const schema = inputSchema[t1Project];
    const newAssumptions: { [key: string]: number } = {};
    
    const initializeFields = (fields: Field[]) => {
      fields.forEach((f) => {
        newAssumptions[f.name] = f.default !== undefined ? f.default : f.min;
      });
    };

    if (Array.isArray(schema)) {
      initializeFields(schema);
    } else {
      Object.values(schema).forEach((groupFields) => {
        initializeFields(groupFields);
      });
    }
    setT1Assumptions(newAssumptions);
    setT1ValidationErrors({});
    setT1GenResult(null);
    setT1AnalysisResult(null);
  }, [t1Project, inputSchema]);

  // Handle Tab 1 Industry Change
  const handleT1IndustryChange = (ind: string) => {
    setT1Industry(ind);
    const projects = Object.keys(registry[ind] || {});
    if (projects.length > 0) {
      setT1Project(projects[0]);
    } else {
      setT1Project("");
    }
  };

  // Handle Tab 1 Assumption field value changes with dynamic validation
  const handleT1AssumptionChange = (name: string, value: number) => {
    const updated = { ...t1Assumptions, [name]: value };
    setT1Assumptions(updated);

    // Call validation endpoint dynamically to verify inputs
    fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_type: t1Project, assumptions: updated }),
    })
      .then((res) => res.json())
      .then((data) => {
        setT1ValidationErrors(data.errors || {});
      })
      .catch((err) => console.error("Validation error:", err));
  };

  // Generate Curated Model
  const handleT1Generate = async () => {
    setT1Generating(true);
    setT1GenResult(null);
    setT1AnalysisResult(null);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_type: t1Project,
          industry: t1Industry,
          assumptions: t1Assumptions,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setT1GenResult(data);
      } else if (data.errors) {
        setT1ValidationErrors(data.errors);
      } else {
        alert("Generation failed: Unknown error.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to communicate with generator backend.");
    } finally {
      setT1Generating(false);
    }
  };

  // Generate AI Analysis
  const handleT1Analyze = async () => {
    if (!t1GenResult) return;
    setT1Analyzing(true);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metrics: t1GenResult.metrics || {},
          project_type: t1Project,
          industry: t1Industry,
          assumptions: t1Assumptions,
          groq_api_key: groqKey || null,
        }),
      });
      if (!res.ok) throw new Error("Analysis failed");
      const data = await res.json();
      setT1AnalysisResult(data);
    } catch (e) {
      console.error(e);
      alert("Failed to generate AI analysis report.");
    } finally {
      setT1Analyzing(false);
    }
  };

  // Handle Tab 2 File Upload Drag/Drop
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadFile(e.target.files[0]);
      setScanResult(null);
      setT2GenResult(null);
    }
  };

  // Run Custom Template Scanner
  const handleT2Scan = async () => {
    if (!uploadFile) return;
    setScanning(true);
    setScanResult(null);
    setT2GenResult(null);
    
    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("driver_sheets", t2DriverSheets);
    formData.append("industry", t2Industry);
    formData.append("project_type", t2Project);

    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Scanning failed.");
      const data = await res.json();
      if (data.success) {
        setScanResult(data);
        
        // Setup initial default assumptions from detected driver registry values
        const initialAssumptions: { [key: string]: number } = {};
        Object.entries(data.driver_registry || {}).forEach(([sheet, entries]: [string, any]) => {
          entries.forEach((e: any) => {
            initialAssumptions[`${sheet}::${e.cell}`] = parseFloat(e.value || 0);
          });
        });
        setT2Assumptions(initialAssumptions);
      }
    } catch (e) {
      console.error(e);
      alert("Error scanning template. Make sure it is a valid .xlsx file.");
    } finally {
      setScanning(false);
    }
  };

  // Generate Custom Scanned Model
  const handleT2Generate = async () => {
    if (!scanResult) return;
    setT2Generating(true);
    setT2GenResult(null);

    const formData = new FormData();
    formData.append("session_id", scanResult.session_id);
    formData.append("industry", scanResult.industry);
    formData.append("project_type", scanResult.project_type);
    formData.append("assumptions_json", JSON.stringify(t2Assumptions));

    try {
      const res = await fetch("/api/generate-scanned", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to write assumptions.");
      const data = await res.json();
      if (data.success) {
        setT2GenResult(data);
      }
    } catch (e) {
      console.error(e);
      alert("Error writing assumptions to custom template.");
    } finally {
      setT2Generating(false);
    }
  };

  // KPI helper thresholds matching backend signals
  const getKpiBadgeClass = (key: string, val: number): string => {
    if (val === undefined || val === null) return "";
    switch (key) {
      case "irr_pct":
        return val >= 14 ? "green" : val >= 10 ? "yellow" : "red";
      case "equity_irr_pct":
        return val >= 18 ? "green" : val >= 13 ? "yellow" : "red";
      case "dscr_avg":
        return val >= 1.3 ? "green" : val >= 1.1 ? "yellow" : "red";
      case "payback_yrs":
        return val <= 8 ? "green" : val <= 12 ? "yellow" : "red";
      case "ebitda_margin_pct":
        return val >= 50 ? "green" : val >= 30 ? "yellow" : "red";
      case "npv_cr":
        return val > 0 ? "green" : "red";
      default:
        return "";
    }
  };

  const getKpiSignalText = (key: string, val: number): string => {
    const badge = getKpiBadgeClass(key, val);
    if (badge === "green") return "🟢 Healthy";
    if (badge === "yellow") return "🟡 Moderate";
    if (badge === "red") return "🔴 Risk Warning";
    return "";
  };

  const METRIC_LABELS: { [key: string]: string } = {
    revenue_cr: "Average Revenue",
    ebitda_cr: "Average EBITDA",
    pat_cr: "Average PAT",
    ebitda_margin_pct: "EBITDA Margin",
    irr_pct: "Project IRR",
    equity_irr_pct: "Equity IRR",
    dscr_avg: "Average DSCR",
    payback_yrs: "Payback Period",
    npv_cr: "Project NPV",
  };

  if (loadingConfig) {
    return (
      <div className="full-page-loader">
        <div className="spinner"></div>
        <p>Loading AI Financial Model Platform configuration...</p>
      </div>
    );
  }

  if (configError) {
    return (
      <div className="main-content" style={{ maxWidth: "800px", margin: "100px auto" }}>
        <div className="alert alert-danger">
          <strong>Backend connection error:</strong> {configError}
          <br />
          Please ensure your FastAPI backend server is running correctly.
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <div className="logo-container">
            <span className="logo-icon">📊</span>
            <div>
              <div className="logo-title">AI Financial Model</div>
              <div className="logo-subtitle">Platform v2.0</div>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-label">Navigation</div>
            <button
              onClick={() => setActiveTab("curated")}
              className={`tab-btn ${activeTab === "curated" ? "active" : ""}`}
              style={{ width: "100%", justifyContent: "flex-start", marginBottom: "0.5rem" }}
            >
              🏭 Curated Templates
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`tab-btn ${activeTab === "upload" ? "active" : ""}`}
              style={{ width: "100%", justifyContent: "flex-start" }}
            >
              📤 Upload Your Template
            </button>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-label">Groq API Key (optional)</div>
            <input
              type="password"
              className="api-key-input"
              value={groqKey}
              onChange={(e) => setGroqKey(e.target.value)}
              placeholder="gsk_..."
            />
            {groqKey ? (
              <div className="alert alert-success" style={{ padding: "0.5rem", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                Active key set
              </div>
            ) : (
              <div className="alert alert-info" style={{ padding: "0.5rem", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                Using rule-based engine
              </div>
            )}
          </div>
        </div>

        <div className="sidebar-footer">
          AI Financial Model Platform v2.0
          <br />
          Next.js + FastAPI + openpyxl
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        <header className="header-banner">
          <h1>📊 AI Financial Model Platform</h1>
          <p>
            Preserves original template structures, formulas, and formatting while dynamically parsing inputs, mapping sheet dependencies, and conducting investment-grade analysis.
          </p>
        </header>

        {/* Tab 1: Curated Templates */}
        {activeTab === "curated" && (
          <div>
            <section className="section-card">
              <h2 className="section-title">🏭 Curated Sector Models</h2>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Select Industry</label>
                  <select
                    className="form-select"
                    value={t1Industry}
                    onChange={(e) => handleT1IndustryChange(e.target.value)}
                  >
                    {Object.keys(registry).map((ind) => (
                      <option key={ind} value={ind}>
                        {ind}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Select Project Type</label>
                  <select
                    className="form-select"
                    value={t1Project}
                    onChange={(e) => setT1Project(e.target.value)}
                  >
                    {Object.keys(registry[t1Industry] || {}).map((proj) => (
                      <option key={proj} value={proj}>
                        {proj}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            {t1Project && inputSchema[t1Project] && (
              <section className="section-card">
                <h2 className="section-title">📝 Assumption Parameters</h2>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
                  Adjust parameters below. Values must stay within logical bounds. Form updates validate instantly against the backend.
                </p>

                {/* Render Dynamic Form */}
                {Array.isArray(inputSchema[t1Project]) ? (
                  /* Flat Input Schema */
                  <div className="grid-3">
                    {(inputSchema[t1Project] as Field[]).map((field) => (
                      <div key={field.name} className="form-group">
                        <label className="form-label">
                          {field.label}
                          {field.unit && <span>({field.unit})</span>}
                        </label>
                        <input
                          type="number"
                          className="form-input"
                          min={field.min}
                          max={field.max}
                          step={field.max <= 1 ? 0.001 : field.max <= 100 ? 0.1 : 1}
                          value={t1Assumptions[field.name] !== undefined ? t1Assumptions[field.name] : field.default}
                          onChange={(e) => handleT1AssumptionChange(field.name, parseFloat(e.target.value))}
                        />
                        {t1ValidationErrors[field.name] && (
                          <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginTop: "0.2rem" }}>
                            ⚠️ {t1ValidationErrors[field.name]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Grouped Input Schema */
                  Object.entries(inputSchema[t1Project] as { [group: string]: Field[] }).map(([groupName, groupFields]) => (
                    <div key={groupName} style={{ marginBottom: "2rem" }}>
                      <h3 style={{ fontSize: "1rem", color: "var(--accent-blue)", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                        {groupName}
                      </h3>
                      <div className="grid-3">
                        {groupFields.map((field) => (
                          <div key={field.name} className="form-group">
                            <label className="form-label">
                              {field.label}
                              {field.unit && <span>({field.unit})</span>}
                            </label>
                            <input
                              type="number"
                              className="form-input"
                              min={field.min}
                              max={field.max}
                              step={field.max <= 1 ? 0.001 : field.max <= 100 ? 0.1 : 1}
                              value={t1Assumptions[field.name] !== undefined ? t1Assumptions[field.name] : field.default}
                              onChange={(e) => handleT1AssumptionChange(field.name, parseFloat(e.target.value))}
                            />
                            {t1ValidationErrors[field.name] && (
                              <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginTop: "0.2rem" }}>
                                ⚠️ {t1ValidationErrors[field.name]}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </section>
            )}

            <section className="section-card" style={{ display: "flex", justifyContent: "flex-start", gap: "1rem" }}>
              <button
                className="btn"
                disabled={t1Generating || Object.keys(t1ValidationErrors).length > 0}
                onClick={handleT1Generate}
              >
                {t1Generating ? (
                  <>
                    <span className="spinner" style={{ marginRight: "0.5rem" }}></span>
                    Generating model...
                  </>
                ) : (
                  "⚡ Generate Financial Model"
                )}
              </button>
            </section>

            {/* Generated Model Results */}
            {t1GenResult && (
              <section className="section-card">
                <h2 className="section-title">📈 Generation Successful</h2>
                <div className="alert alert-success">
                  Financial model generated successfully! Original formulas, styles, and sheet mappings have been preserved.
                </div>
                
                <div style={{ margin: "1.5rem 0" }}>
                  <a
                    href={`/api/download-model?filename=${t1GenResult.filename}`}
                    className="btn btn-success"
                    style={{ textDecoration: "none" }}
                  >
                    📥 Download Excel Model
                  </a>
                </div>

                <div className="kpis-container">
                  <div className="kpi-section-title">Profitability Metrics</div>
                  <div className="kpi-grid">
                    {["revenue_cr", "ebitda_cr", "pat_cr", "ebitda_margin_pct"].map((key) => {
                      const val = t1GenResult.metrics?.[key];
                      const unit = key.includes("pct") ? "%" : " ₹ Cr";
                      return (
                        <div key={key} className={`kpi-card ${getKpiBadgeClass(key, val)}`}>
                          <div className="kpi-label">{METRIC_LABELS[key]}</div>
                          <div className="kpi-value">{val !== undefined ? `${val.toFixed(2)}${unit}` : "—"}</div>
                          <div className="kpi-indicator">{getKpiSignalText(key, val)}</div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="kpi-section-title">Investment Returns</div>
                  <div className="kpi-grid">
                    {["irr_pct", "equity_irr_pct", "dscr_avg", "payback_yrs", "npv_cr"].map((key) => {
                      const val = t1GenResult.metrics?.[key];
                      const unit = key.includes("pct") ? "%" : key.includes("yrs") ? " Yrs" : key.includes("dscr") ? "x" : " ₹ Cr";
                      return (
                        <div key={key} className={`kpi-card ${getKpiBadgeClass(key, val)}`}>
                          <div className="kpi-label">{METRIC_LABELS[key]}</div>
                          <div className="kpi-value">{val !== undefined ? `${val.toFixed(2)}${unit}` : "—"}</div>
                          <div className="kpi-indicator">{getKpiSignalText(key, val)}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "1.5rem", marginTop: "2rem" }}>
                  <h3 style={{ fontSize: "1.1rem", marginBottom: "1rem", color: "#fff" }}>🤖 AI Investment Memo</h3>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                    Analyze simulated returns and risk profiles automatically. Uses Llama-3.3 on Groq (if key provided) or deterministic rules.
                  </p>
                  <button className="btn" onClick={handleT1Analyze} disabled={t1Analyzing}>
                    {t1Analyzing ? (
                      <>
                        <span className="spinner" style={{ marginRight: "0.5rem" }}></span>
                        Generating Analysis...
                      </>
                    ) : (
                      "🤖 Generate Investment Analysis"
                    )}
                  </button>
                </div>

                {t1AnalysisResult && (
                  <div style={{ marginTop: "1.5rem" }}>
                    <div className="alert alert-info">
                      {t1AnalysisResult.source === "groq" ? "🤖 AI-Generated (Groq Llama 3)" : "📐 Rule-Based Professional Analysis"}
                    </div>

                    <div style={{ display: "flex", gap: "1rem", margin: "1.5rem 0" }}>
                      <a
                        href={`/api/download-report?filename=${t1AnalysisResult.report_filename}`}
                        className="btn btn-secondary"
                        style={{ textDecoration: "none" }}
                      >
                        📄 Download PDF Report
                      </a>
                      <a
                        href={`/api/download-report?filename=${t1AnalysisResult.report_filename.replace(".pdf", ".md")}`}
                        className="btn btn-secondary"
                        style={{ textDecoration: "none" }}
                      >
                        📝 Download Markdown Memo
                      </a>
                    </div>

                    <h4 style={{ color: "#fff", marginBottom: "1rem" }}>📋 Investment Memo Content</h4>
                    <div
                      className="memo-container"
                      dangerouslySetInnerHTML={{
                        __html: t1AnalysisResult.memo
                          .replace(/\n/g, "<br />")
                          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                          .replace(/### (.*?)(<br \/>)/g, "<h3>$1</h3>")
                          .replace(/## (.*?)(<br \/>)/g, "<h2>$1</h2>")
                      }}
                    />
                  </div>
                )}
              </section>
            )}
          </div>
        )}

        {/* Tab 2: Upload Custom Excel Templates */}
        {activeTab === "upload" && (
          <div>
            <section className="section-card">
              <h2 className="section-title">📤 Upload Custom Template</h2>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
                Upload any Excel template. The platform scanner parses the sheets to extract inputs, and maps formulas dynamically to construct input fields automatically.
              </p>

              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Driver Input Sheets (comma-separated)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={t2DriverSheets}
                    onChange={(e) => setT2DriverSheets(e.target.value)}
                    placeholder="NTBA, CAPEX, TBA"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Target Industry / Sector</label>
                  <input
                    type="text"
                    className="form-input"
                    value={t2Industry}
                    onChange={(e) => setT2Industry(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid-2" style={{ marginTop: "1rem" }}>
                <div className="form-group">
                  <label className="form-label">Target Project Type</label>
                  <input
                    type="text"
                    className="form-input"
                    value={t2Project}
                    onChange={(e) => setT2Project(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Select Template File (.xlsx)</label>
                  <input
                    type="file"
                    className="form-input"
                    accept=".xlsx"
                    onChange={handleFileChange}
                    style={{ padding: "0.6rem" }}
                  />
                </div>
              </div>

              <div style={{ marginTop: "1.5rem" }}>
                <button className="btn" disabled={scanning || !uploadFile} onClick={handleT2Scan}>
                  {scanning ? (
                    <>
                      <span className="spinner" style={{ marginRight: "0.5rem" }}></span>
                      Scanning template...
                    </>
                  ) : (
                    "🔍 Run Template Scanner"
                  )}
                </button>
              </div>
            </section>

            {/* Display Template Scanning Diagnostic Panels */}
            {scanResult && scanResult.scan_result && (
              <div>
                <section className="section-card">
                  <h2 className="section-title">📊 Scanner Diagnostics</h2>
                  
                  <div className="kpi-grid" style={{ marginBottom: "2rem" }}>
                    <div className="kpi-card">
                      <div className="kpi-label">Sheets Detected</div>
                      <div className="kpi-value">{scanResult.scan_result.summary.sheet_count}</div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">Formula Cells</div>
                      <div className="kpi-value">{scanResult.scan_result.summary.total_formula_cells}</div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">Numeric Cells</div>
                      <div className="kpi-value">{scanResult.scan_result.summary.total_numeric_cells}</div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">Driver Candidates</div>
                      <div className="kpi-value">{scanResult.scan_result.summary.total_driver_candidates}</div>
                    </div>
                  </div>

                  <h3 style={{ fontSize: "1rem", color: "#fff", marginBottom: "1rem" }}>📋 Sheet Classifications</h3>
                  <div className="table-wrapper">
                    <table className="custom-table">
                      <thead>
                        <tr>
                          <th>Sheet</th>
                          <th>Classification</th>
                          <th>Formula Cells</th>
                          <th>Numeric Inputs</th>
                          <th>Is Driver Sheet</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(scanResult.scan_result.sheet_structure).map(([sheet, details]) => (
                          <tr key={sheet}>
                            <td><strong>{sheet}</strong></td>
                            <td style={{ textTransform: "capitalize" }}>{details.classification}</td>
                            <td>{details.formula_cell_count}</td>
                            <td>{details.numeric_cell_count}</td>
                            <td>{details.is_driver_sheet ? "✅ Yes" : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <h3 style={{ fontSize: "1rem", color: "#fff", marginBottom: "1rem", marginTop: "2rem" }}>🔗 Cross-Sheet Dependencies</h3>
                  <div style={{ backgroundColor: "rgba(0,0,0,0.2)", borderRadius: "8px", padding: "1rem" }}>
                    {Object.entries(scanResult.dependency_map).filter(([_, refs]) => refs.length > 0).map(([sheet, refs]) => (
                      <div key={sheet} style={{ marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span className="cell-badge" style={{ backgroundColor: "rgba(99, 102, 241, 0.2)", color: "#c7d2fe" }}>
                          {sheet}
                        </span>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>reads from</span>
                        <div className="chip-container">
                          {refs.map((r) => (
                            <span key={r} className="sheet-chip">
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="section-card">
                  <h2 className="section-title">⚙️ Detected Driver Inputs</h2>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
                    Below are the driver inputs extracted from the scanned workbook. Edit their values to update the custom spreadsheet.
                  </p>

                  {Object.entries(scanResult.driver_registry).map(([sheetName, entries]) => (
                    <div key={sheetName} style={{ marginBottom: "2rem" }}>
                      <h3 style={{ fontSize: "1rem", color: "var(--accent-blue)", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                        {sheetName} Inputs
                      </h3>
                      
                      <div className="grid-3">
                        {entries.map((entry) => {
                          const key = `${sheetName}::${entry.cell}`;
                          const val = t2Assumptions[key] !== undefined ? t2Assumptions[key] : entry.value;
                          
                          // Heuristic configurations for custom fields
                          let step = 1;
                          let format = "%.2f";
                          if (entry.value > 0 && entry.value <= 1) {
                            step = 0.01;
                            format = "%.4f";
                          } else if (entry.value > 1 && entry.value <= 100) {
                            step = 0.1;
                          } else if (entry.value > 1000) {
                            step = 10;
                          }

                          return (
                            <div key={entry.cell} className="form-group">
                              <label className="form-label" title={entry.raw_label}>
                                {entry.label} <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.7rem" }}>({entry.cell})</span>
                              </label>
                              <input
                                type="number"
                                className="form-input"
                                step={step}
                                value={val}
                                onChange={(e) => setT2Assumptions({ ...t2Assumptions, [key]: parseFloat(e.target.value) || 0 })}
                              />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                  <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "1.5rem", marginTop: "2rem" }}>
                    <button className="btn" disabled={t2Generating} onClick={handleT2Generate}>
                      {t2Generating ? (
                        <>
                          <span className="spinner" style={{ marginRight: "0.5rem" }}></span>
                          Generating model...
                        </>
                      ) : (
                        "⚡ Generate Scanned Model"
                      )}
                    </button>
                  </div>

                  {t2GenResult && (
                    <div style={{ marginTop: "1.5rem" }}>
                      <div className="alert alert-success">
                        Scanned financial model generated successfully!
                      </div>
                      <a
                        href={`/api/download-model?filename=${t2GenResult.filename}`}
                        className="btn btn-success"
                        style={{ textDecoration: "none", marginTop: "0.5rem" }}
                      >
                        📥 Download Scanned Excel Model
                      </a>
                    </div>
                  )}
                </section>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
