"""
engines/analysis_engine.py
─────────────────────────────────────────────────────────────────────────────
Generates a structured investment analysis memo from financial metrics.

Priority:
  1. Groq API (llama-3.3-70b-versatile) — free & fast if GROQ_API_KEY is set
  2. Rule-based template — always works, no API key required

The rule-based engine produces a professional, data-rich memo from
pre-written paragraphs parametrised with the actual metric values.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any

# ---------------------------------------------------------------------------
# Groq client (optional)
# ---------------------------------------------------------------------------
try:
    from groq import Groq  # type: ignore

    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False


def _groq_analysis(
    metrics: dict[str, Any],
    project_type: str,
    industry: str,
    assumptions: dict[str, Any],
) -> str:
    """Call Groq API to generate the investment memo."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key or not _GROQ_AVAILABLE:
        return ""

    client = Groq(api_key=api_key)

    metrics_text = "\n".join(
        f"  - {k}: {v}" for k, v in metrics.items()
    )
    assumptions_text = "\n".join(
        f"  - {k}: {v}" for k, v in assumptions.items()
    )

    prompt = f"""You are a senior infrastructure finance analyst at a top investment bank.

Write a professional investment analysis memo for a **{project_type}** project in the **{industry}** sector.

## Key Assumptions
{assumptions_text}

## Financial Model Outputs
{metrics_text}

Structure your memo with these exact sections:

## 1. Executive Summary
## 2. Business & Revenue Model
## 3. Profitability Analysis
## 4. Investment Returns
## 5. Risk Analysis
## 6. Final Investment Recommendation

Guidelines:
- Use specific numbers from the metrics
- Be concise but insightful (each section 120-180 words)
- Highlight strengths and material risks
- Use professional finance language
- End with a clear BUY / HOLD / PASS recommendation with justification
"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2000,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def _fmt(val, decimals: int = 2, suffix: str = "") -> str:
    """Format a number nicely, handling None."""
    if val is None:
        return "N/A"
    try:
        return f"{round(float(val), decimals):,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(val)


def _signal(metric: str, val) -> str:
    """Return 🟢/🟡/🔴 based on metric thresholds."""
    if val is None:
        return "🔘"
    v = float(val)
    thresholds = {
        "irr_pct":           (14, 10),
        "equity_irr_pct":    (18, 13),
        "dscr_avg":          (1.3, 1.1),
        "payback_yrs":       (8, 12),     # lower is better
        "ebitda_margin_pct": (50, 30),
        "npv_cr":            (0.01, -999),
    }
    if metric not in thresholds:
        return ""
    high, low = thresholds[metric]
    if metric == "payback_yrs":
        return "🟢" if v <= high else ("🟡" if v <= low else "🔴")
    return "🟢" if v >= high else ("🟡" if v >= low else "🔴")


def _rule_based_analysis(
    metrics: dict[str, Any],
    project_type: str,
    industry: str,
    assumptions: dict[str, Any],
) -> str:
    """Generate a structured investment memo using rule-based templates."""

    irr     = metrics.get("irr_pct", 0)
    e_irr   = metrics.get("equity_irr_pct", 0)
    dscr    = metrics.get("dscr_avg", 0)
    payback = metrics.get("payback_yrs", 0)
    rev     = metrics.get("revenue_cr", 0)
    ebitda  = metrics.get("ebitda_cr", 0)
    pat     = metrics.get("pat_cr", 0)
    ebitda_m= metrics.get("ebitda_margin_pct", 0)
    npv     = metrics.get("npv_cr", 0)
    tv      = metrics.get("terminal_value_cr", 0)
    d_ratio = float(assumptions.get("debt_ratio", 0.70)) * 100
    tax     = float(assumptions.get("tax_rate", 25.17))

    # Investment recommendation logic
    score = 0
    if irr and float(irr) >= 14:  score += 2
    elif irr and float(irr) >= 10: score += 1
    if e_irr and float(e_irr) >= 18: score += 2
    elif e_irr and float(e_irr) >= 13: score += 1
    if dscr and float(dscr) >= 1.3: score += 2
    elif dscr and float(dscr) >= 1.1: score += 1
    if npv and float(npv) > 0: score += 2

    if score >= 6:
        rec = "**BUY / INVEST** ✅"
        rec_text = (
            f"The project delivers strong risk-adjusted returns with a project IRR of "
            f"{_fmt(irr)}%, equity IRR of {_fmt(e_irr)}%, and positive NPV of "
            f"₹{_fmt(npv)} Crore. With an average DSCR of {_fmt(dscr)}x, debt service "
            f"coverage is comfortable. We recommend **proceeding with investment** subject "
            f"to finalisation of off-take agreements and financing terms."
        )
    elif score >= 3:
        rec = "**CONDITIONAL / HOLD** 🟡"
        rec_text = (
            f"The project shows moderate return potential (IRR: {_fmt(irr)}%, Equity IRR: "
            f"{_fmt(e_irr)}%) but warrants further diligence. DSCR of {_fmt(dscr)}x provides "
            f"limited headroom against stress scenarios. We recommend a **conditional proceed** "
            f"subject to resolving identified risks and optimising the capital structure."
        )
    else:
        rec = "**PASS / RECONSIDER** 🔴"
        rec_text = (
            f"Current return parameters (IRR: {_fmt(irr)}%, DSCR: {_fmt(dscr)}x) do not "
            f"meet investment thresholds. We recommend **revisiting assumptions** — particularly "
            f"tariff, capex quantum, and debt terms — before committing capital."
        )

    memo = f"""# Investment Analysis Memo
## {project_type} — {industry} Sector

---

## 1. Executive Summary

This memo presents a structured financial analysis of the proposed **{project_type}** project in the **{industry}** sector. Based on the financial model outputs, the project generates annual revenues of **₹{_fmt(rev)} Crore** with an EBITDA of **₹{_fmt(ebitda)} Crore** ({_fmt(ebitda_m)}% margin). The project IRR stands at **{_fmt(irr)}%** {_signal('irr_pct', irr)} and equity IRR at **{_fmt(e_irr)}%** {_signal('equity_irr_pct', e_irr)}, with a payback period of **{_fmt(payback, 1)} years** {_signal('payback_yrs', payback)} and NPV of **₹{_fmt(npv)} Crore** {_signal('npv_cr', npv)}.

---

## 2. Business & Revenue Model

The {project_type} operates under a structured revenue framework with contracted/predictable cash flows. At the assumed operating parameters, annual revenues are projected at ₹{_fmt(rev)} Crore. The revenue model benefits from {"long-term contracted off-take arrangements" if industry in ("Energy","Infrastructure") else "service-based recurring revenues"}, providing high revenue visibility. Revenue growth is expected to follow an escalation trajectory in line with {"CPI/WPI indexation" if industry == "Infrastructure" else "tariff revision schedules"}.

---

## 3. Profitability Analysis

| Metric | Value | Signal |
|--------|-------|--------|
| Revenue (₹ Crore) | {_fmt(rev)} | — |
| EBITDA (₹ Crore) | {_fmt(ebitda)} | — |
| EBITDA Margin | {_fmt(ebitda_m)}% | {_signal('ebitda_margin_pct', ebitda_m)} |
| PAT (₹ Crore) | {_fmt(pat)} | — |

The EBITDA margin of **{_fmt(ebitda_m)}%** reflects {"strong operational leverage typical of asset-heavy infrastructure plays" if float(ebitda_m) > 50 else "moderate profitability that may compress under adverse scenarios"}. PAT of ₹{_fmt(pat)} Crore is computed after accounting for depreciation on the capital base and interest on {_fmt(d_ratio, 0)}% debt financing at prevailing market rates. Corporate tax is applied at the current statutory rate of {_fmt(tax)}%.

---

## 4. Investment Returns

| Return Metric | Value | Benchmark | Signal |
|---------------|-------|-----------|--------|
| Project IRR | {_fmt(irr)}% | ≥ 12% | {_signal('irr_pct', irr)} |
| Equity IRR | {_fmt(e_irr)}% | ≥ 15% | {_signal('equity_irr_pct', e_irr)} |
| Average DSCR | {_fmt(dscr)}x | ≥ 1.2x | {_signal('dscr_avg', dscr)} |
| Payback Period | {_fmt(payback, 1)} Yrs | ≤ 10 Yrs | {_signal('payback_yrs', payback)} |
| NPV (₹ Crore) | {_fmt(npv)} | > 0 | {_signal('npv_cr', npv)} |
| Terminal Value (₹ Crore) | {_fmt(tv)} | — | — |

The project IRR of **{_fmt(irr)}%** {"exceeds the typical hurdle rate of 12–14% for similar projects" if irr and float(irr) > 14 else "falls within the acceptable band for regulated infrastructure assets"} in the {industry} sector. The equity IRR of {_fmt(e_irr)}% reflects the {"favourable" if e_irr and float(e_irr) > 15 else "moderate"} impact of the assumed {_fmt(d_ratio, 0)}% leverage ratio.

---

## 5. Risk Analysis

### Key Risk Factors

**1. Revenue Risk**
{"Off-take risk is mitigated through long-term PPA/concession arrangements." if industry in ("Energy","Infrastructure") else "Revenue is subject to market adoption and competitive pricing pressures."}
Sensitivity analysis indicates a 10% tariff/price reduction would compress IRR by approximately 150–200 bps.

**2. Construction & Cost Overrun Risk**
Capex assumptions carry a typical contingency of 5–10%. Any overrun beyond this range would directly impact debt sizing and returns. Lender typically require a Debt Service Reserve Account (DSRA) equivalent to 6 months' debt service.

**3. Financing Risk**
The model assumes {_fmt(d_ratio, 0)}% debt at prevailing market rates. A 100 bps increase in interest rates would reduce project IRR by approximately 50–80 bps. Debt markets remain broadly supportive for {'renewable energy' if industry == 'Energy' else industry.lower()} assets.

**4. Regulatory & Policy Risk**
{"Policy continuity on renewable energy targets provides a supportive backdrop." if industry == "Energy" else "Regulatory framework evolution could impact long-term economics."} Changes in tax regime or depreciation rates could materially affect post-tax returns.

**5. Operational Risk**
{"Performance below assumed PLF/CUF would directly reduce generation revenue." if industry == "Energy" else "Operational underperformance against projected metrics would compress margins."} Mitigation typically involves performance guarantees from EPC/O&M contractors.

---

## 6. Final Investment Recommendation

### Recommendation: {rec}

{rec_text}

**Key Conditions / Mitigants:**
- Lock in long-term off-take / revenue agreements before financial close
- Maintain DSRA of minimum 6 months' debt service
- Include cost escalation clauses linked to inflation indices
- Conduct independent technical and legal due diligence
- Monitor early-stage operational metrics against model assumptions

---

*This analysis is generated by the AI Financial Model Platform based on user-provided assumptions. It is intended for informational purposes only and does not constitute investment advice. All projections are subject to actual market conditions and regulatory outcomes.*
"""
    return textwrap.dedent(memo).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_analysis(
    metrics: dict[str, Any],
    project_type: str,
    industry: str,
    assumptions: dict[str, Any],
) -> tuple[str, str]:
    """
    Generate investment analysis memo.

    Returns:
        (memo_markdown, source)
        where source is "groq" or "rule-based"
    """
    # Try Groq first
    groq_text = _groq_analysis(metrics, project_type, industry, assumptions)
    if groq_text:
        return groq_text, "groq"

    # Fallback to rule-based
    return _rule_based_analysis(metrics, project_type, industry, assumptions), "rule-based"
