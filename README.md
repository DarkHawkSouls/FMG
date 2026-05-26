# AI Financial Model Platform

> **Production-grade AI-assisted financial modeling platform**  
> Generate professional Excel financial models with preserved templates, extract KPIs, and produce AI investment analysis reports — all from a web interface.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-financial-model-platform.git
cd ai-financial-model-platform
pip install -r requirements.txt
```

### 2. Create Demo Templates

```bash
python scripts/create_demo_templates.py
```

This generates stub `.xlsx` templates in the `templates/` directory with the correct 20-sheet structure.

### 3. Run the App

```bash
streamlit run webapp/app.py
```

Open your browser at **http://localhost:8501**

---

## 📁 Project Structure

```
ai-financial-model-platform/
│
├── templates/                      # Excel template files by industry
│   ├── energy/
│   │   ├── solar_project_model.xlsx
│   │   └── wind_project_model.xlsx
│   ├── infrastructure/
│   │   ├── smart_meter_model.xlsx
│   │   └── highway_ppp_model.xlsx
│   ├── telecom/
│   │   └── network_rollout_model.xlsx
│   └── manufacturing/
│       └── plant_expansion_model.xlsx
│
├── config/
│   ├── template_registry.json      # Industry → Project → Template mapping
│   ├── input_schema.json           # User input field definitions per project type
│   └── driver_registry.json        # Cell addresses for driver inputs (NTBA/CAPEX/TBA)
│
├── engines/
│   ├── driver_extractor.py         # Scans templates to detect driver cells
│   ├── assumption_mapper.py        # Maps assumptions to cell addresses
│   ├── template_writer.py          # Writes values into template (formula-safe)
│   ├── validation_engine.py        # Validates assumption inputs
│   ├── metrics_extractor.py        # Reads KPIs from generated models
│   ├── analysis_engine.py          # AI investment memo generator
│   └── report_generator.py         # PDF / Markdown report exporter
│
├── scripts/
│   └── create_demo_templates.py    # One-time demo template stub creator
│
├── webapp/
│   └── app.py                      # Streamlit web application
│
├── output/
│   ├── generated_models/           # Generated Excel output files
│   └── reports/                    # PDF and Markdown reports
│
├── .streamlit/
│   └── config.toml                 # Dark theme configuration
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🏭 Supported Industries & Project Types

| Industry        | Project Types                               |
|-----------------|---------------------------------------------|
| Energy          | Solar Project, Wind Project                 |
| Infrastructure  | Smart Meter Rollout, Highway PPP            |
| Telecom         | Network Rollout                             |
| Manufacturing   | Plant Expansion                             |

---

## ⚙️ How It Works

### Template Safety (Critical Rules)

The platform **NEVER** modifies:
- Any formula in any sheet
- Sheet structure or sheet names
- Cell formatting or styles

It **only writes plain numeric values** into designated driver cells in:
- `NTBA` — Operating assumptions (capacity, tariff, PLF, etc.)
- `CAPEX` — Capital expenditure assumptions
- `TBA` — Financing and tax assumptions (debt ratio, interest rate, tax rate)

All other sheets (Financials, Ratios, Monthly, etc.) are computed by Excel formulas from these inputs.

### Workflow

```
User Assumptions
       │
       ▼
Validation Engine ──► Error messages (if invalid)
       │
       ▼
Assumption Mapper ──► {Sheet: {Cell: Value}}
       │
       ▼
Template Writer ──► Copies template, writes values only to NTBA/CAPEX/TBA
       │
       ▼
Generated Excel Model (.xlsx)
       │
       ▼
Metrics Extractor ──► {IRR, NPV, DSCR, Payback, ...}
       │
       ▼
Analysis Engine ──► Investment Memo (Groq AI or rule-based)
       │
       ▼
Report Generator ──► PDF / Markdown download
```

### Smart Meter (demo/idemo)

- `Smart Meter Rollout` now points to `examples/idemo.xlsx` in `config/template_registry.json`.
- Grouped UI schema and semantic input names are in `config/smart_meter_input_schema.json`.
- Driver-cell mapping is in `config/smart_meter_driver_registry.json`.
- Mapping notes are in `docs/smart_meter_template_mapping.md`.

---

## 🔧 Adding Real Templates

1. Place your `.xlsx` template in the appropriate `templates/` subfolder
2. Update `config/template_registry.json` to point to the new file
3. Run the driver extractor to detect input cells:

```bash
python engines/driver_extractor.py \
    --template templates/energy/my_solar_model.xlsx \
    --project "Solar Project"
```

4. Review and adjust `config/driver_registry.json` if needed
5. Restart the Streamlit app

---

## 🤖 AI Analysis

The platform supports two analysis modes:

| Mode | Description | Requirement |
|------|-------------|-------------|
| **Groq AI** | `llama-3.3-70b-versatile` via Groq API | Free API key from [console.groq.com](https://console.groq.com) |
| **Rule-Based** | Deterministic professional memo | No API key needed |

Enter your Groq API key in the sidebar, or set it as an environment variable:

```bash
export GROQ_API_KEY=gsk_...
```

---

## ☁️ Deployment (Streamlit Cloud)

1. Push repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set **Main file path**: `webapp/app.py`
5. Add `GROQ_API_KEY` in the **Secrets** section (optional)
6. Deploy!

> **Note**: Demo templates are created at runtime by `scripts/create_demo_templates.py`.  
> For Streamlit Cloud, commit the generated template files or add a startup hook.

---

## 🛠️ Development

### Run driver extractor on a template

```bash
python engines/driver_extractor.py \
    --template templates/energy/solar_project_model.xlsx \
    --project "Solar Project"
```

### Validate the writer engine

```bash
python -c "from engines.template_writer import demo_write; demo_write('Solar Project')"
```

### Run tests

```bash
pytest tests/ -v
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web application framework |
| `openpyxl` | Excel file reading and writing |
| `pandas` | Data manipulation and display |
| `numpy` | Numerical calculations |
| `reportlab` | PDF report generation |
| `groq` | Groq API client for AI memos |
| `python-dotenv` | Environment variable loading |

---

## ⚖️ Disclaimer

This platform generates financial projections based on user-provided assumptions. All outputs are for **informational purposes only** and do not constitute investment advice. Actual financial results may differ materially from projections.

---

*Built with ❤️ using Streamlit + openpyxl*
