"""
ValueOS FDE Demo — Report Renderer
Converts the agentic analysis JSON into a self-contained HTML report
that renders beautifully in any browser. The FDE opens this URL in the
demo to show the client their personalized ROI report in real-time.
"""
import json
from datetime import datetime, timezone


def render_html_report(analysis: dict, company: dict) -> str:
    """Generate a self-contained HTML executive report from the analysis bundle."""
    rpt = analysis.get("pass3_report", {})
    attr = analysis.get("pass1_attribution", {})
    opt = analysis.get("pass2_optimization", {})
    es = rpt.get("executive_summary", {})
    csa = rpt.get("current_state_analysis", {})
    roi = rpt.get("roi_attribution_detail", {})
    optim = rpt.get("optimization_recommendations", {})
    roadmap = rpt.get("implementation_roadmap", {})
    risk = rpt.get("risk_and_governance", {})
    appendix = rpt.get("appendix", {})
    ps = attr.get("portfolio_summary", {})
    os_ = opt.get("optimization_summary", {})
    cm = csa.get("critical_metrics", {})
    company_name = company.get("name", "Client")

    def fmt(v):
        if isinstance(v, (int, float)):
            if abs(v) >= 1000:
                return f"${v:,.0f}"
            return f"${v:,.2f}"
        return str(v)

    def pct(v):
        if isinstance(v, (int, float)):
            return f"{v:.1f}%"
        return str(v)

    # Build prioritized actions rows
    actions_html = ""
    for a in optim.get("prioritized_actions", []):
        eff_class = {"low": "tag-green", "medium": "tag-yellow", "high": "tag-red"}.get(str(a.get("effort", "")).lower(), "tag-yellow")
        actions_html += f"""<tr>
            <td><strong>{a.get('priority','')}</strong></td>
            <td><strong>{a.get('title','')}</strong><br><span class="sub">{a.get('description','')}</span></td>
            <td class="num">{fmt(a.get('annual_savings_usd', 0))}</td>
            <td><span class="tag {eff_class}">{a.get('effort','').upper()}</span></td>
            <td>{a.get('timeline','')}</td></tr>"""

    # Project attribution rows
    proj_rows = ""
    for p in attr.get("project_attributions", []):
        roi_class = "green" if p.get("roi_score", 0) >= 60 else "yellow" if p.get("roi_score", 0) >= 30 else "red"
        proj_rows += f"""<tr>
            <td><strong>{p.get('project_name','')}</strong><br><span class="sub">{p.get('department','')}</span></td>
            <td class="num">{fmt(p.get('monthly_total_cost_usd', 0))}/mo</td>
            <td><span class="score score-{roi_class}">{p.get('roi_score', 0)}</span></td>
            <td>{p.get('value_alignment','').upper()}</td>
            <td>{p.get('utilization_efficiency','')}</td>
            <td class="sub">{p.get('roi_rationale','')[:120]}</td></tr>"""

    # Quick wins
    qw_html = ""
    for qw in opt.get("quick_wins", [])[:5]:
        qw_html += f"""<div class="qw-card">
            <div class="qw-savings">{fmt(qw.get('monthly_savings_usd', 0))}/mo</div>
            <h4>{qw.get('title','')}</h4>
            <p>{qw.get('description','')}</p>
            <div class="qw-meta">{qw.get('effort','').upper()} effort · {qw.get('timeline_days', 0)} days</div></div>"""

    # Roadmap phases
    phase_html = ""
    for ph in roadmap.get("phases", []):
        items = "".join(f"<li>{a}</li>" for a in ph.get("actions", []))
        phase_html += f"""<div class="phase-card">
            <h4>{ph.get('phase','')}</h4>
            <div class="phase-savings">Expected savings: {fmt(ph.get('expected_savings_usd', 0))}</div>
            <ul>{items}</ul>
            <div class="qw-meta">{ph.get('resources_needed','')}</div></div>"""

    # Risk rows
    risk_rows = ""
    for r in risk.get("top_risks", []):
        sev_class = {"high": "tag-red", "medium": "tag-yellow", "low": "tag-green"}.get(str(r.get("severity","")).lower(), "tag-yellow")
        risk_rows += f"""<tr>
            <td>{r.get('risk','')}</td>
            <td><span class="tag {sev_class}">{str(r.get('severity','')).upper()}</span></td>
            <td>{r.get('mitigation','')}</td></tr>"""

    # Top performers / underperformers
    top_perf = "".join(f"<li><strong>{t.get('project','')}</strong> (ROI: {t.get('roi_score',0)}) — {t.get('why','')}</li>"
                       for t in roi.get("top_performers", []))
    under_perf = "".join(f"<li><strong>{u.get('project','')}</strong> (ROI: {u.get('roi_score',0)}) — {u.get('issue','')} → <em>{u.get('recommendation','')}</em></li>"
                        for u in roi.get("underperformers", []))

    grade = csa.get("health_grade", "C")
    grade_color = {"A": "#1DB954", "B": "#4CAF50", "C": "#FF9800", "D": "#FF5722", "F": "#C62828"}.get(grade, "#999")

    now = datetime.now(timezone.utc).strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{rpt.get('report_title', f'AI ROI Report — {company_name}')}</title>
<style>
:root {{ --green: #1DB954; --dark: #1A1A2E; --gray: #F5F5F5; --border: #E0E0E0; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; color: #1a1a1a; line-height: 1.6; background: #fff; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 0 40px; }}
header {{ background: var(--dark); color: white; padding: 48px 0 40px; }}
header .container {{ display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 20px; }}
.brand {{ font-size: 13px; letter-spacing: 3px; color: var(--green); font-weight: 700; margin-bottom: 8px; }}
header h1 {{ font-size: 28px; font-weight: 800; line-height: 1.2; }}
header .date {{ font-size: 14px; color: #aaa; text-align: right; }}
header .badge {{ background: var(--green); color: var(--dark); padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 13px; display: inline-block; margin-top: 8px; }}
.kpi-bar {{ background: var(--gray); border-bottom: 1px solid var(--border); padding: 28px 0; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 24px; }}
.kpi {{ text-align: center; }}
.kpi-value {{ font-size: 28px; font-weight: 800; color: var(--dark); }}
.kpi-value.green {{ color: var(--green); }}
.kpi-label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }}
section {{ padding: 40px 0; border-bottom: 1px solid var(--border); }}
section:last-of-type {{ border-bottom: none; }}
h2 {{ font-size: 22px; font-weight: 700; color: var(--dark); margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid var(--green); display: inline-block; }}
h3 {{ font-size: 17px; font-weight: 600; color: #333; margin: 20px 0 8px; }}
p, li {{ font-size: 15px; color: #333; }}
.narrative {{ font-size: 15px; line-height: 1.8; color: #444; margin-bottom: 16px; white-space: pre-line; }}
.callout {{ background: #EBF9F0; border-left: 4px solid var(--green); padding: 16px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
.callout.warn {{ background: #FFF8E1; border-color: #FF9800; }}
.callout p {{ margin: 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
th {{ background: var(--dark); color: white; padding: 10px 12px; text-align: left; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
tr:hover {{ background: #f9f9f9; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
.sub {{ font-size: 12px; color: #888; }}
.tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }}
.tag-green {{ background: #E8F5E9; color: #2E7D32; }}
.tag-yellow {{ background: #FFF8E1; color: #F57F17; }}
.tag-red {{ background: #FFEBEE; color: #C62828; }}
.score {{ display: inline-block; width: 40px; height: 40px; line-height: 40px; text-align: center; border-radius: 50%; font-weight: 800; font-size: 14px; color: white; }}
.score-green {{ background: #1DB954; }}
.score-yellow {{ background: #FF9800; }}
.score-red {{ background: #F44336; }}
.grade-box {{ display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 16px; font-size: 36px; font-weight: 900; color: white; }}
.qw-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 16px 0; }}
.qw-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 20px; position: relative; }}
.qw-card h4 {{ font-size: 15px; margin-bottom: 6px; }}
.qw-card p {{ font-size: 13px; color: #666; }}
.qw-savings {{ position: absolute; top: 12px; right: 16px; font-weight: 800; color: var(--green); font-size: 16px; }}
.qw-meta {{ font-size: 12px; color: #999; margin-top: 8px; }}
.phase-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin: 12px 0; }}
.phase-card h4 {{ color: var(--dark); font-size: 16px; margin-bottom: 4px; }}
.phase-savings {{ font-size: 14px; color: var(--green); font-weight: 700; margin-bottom: 10px; }}
.phase-card ul {{ padding-left: 20px; }}
.phase-card li {{ font-size: 13px; margin-bottom: 4px; }}
.findings {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 16px 0; }}
.findings ul {{ padding-left: 18px; }}
.findings li {{ margin-bottom: 8px; font-size: 14px; }}
footer {{ background: var(--dark); color: #888; padding: 30px 0; font-size: 12px; text-align: center; }}
footer strong {{ color: var(--green); }}
@media print {{ header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
@media (max-width: 768px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} .findings {{ grid-template-columns: 1fr; }} }}
</style></head><body>

<header><div class="container">
  <div><div class="brand">VALUEOS · AI ROI ATTRIBUTION</div>
    <h1>{rpt.get('report_title', f'AI ROI Report — {company_name}')}</h1></div>
  <div><div class="date">Generated {now}</div>
    <div class="date">{company.get('industry', '')} · {company.get('size', '')} employees</div>
    <div class="badge">CONFIDENTIAL</div></div>
</div></header>

<div class="kpi-bar"><div class="container"><div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{fmt(ps.get('total_monthly_ai_spend_usd', cm.get('total_annual_ai_spend', 0) / 12))}</div><div class="kpi-label">Monthly AI Spend</div></div>
  <div class="kpi"><div class="kpi-value green">{fmt(os_.get('annual_savings_usd', optim.get('total_annual_savings_potential_usd', 0)))}</div><div class="kpi-label">Annual Savings Potential</div></div>
  <div class="kpi"><div class="kpi-value">{pct(os_.get('savings_percentage', optim.get('savings_as_pct_of_spend', 0)))}</div><div class="kpi-label">Cost Reduction</div></div>
  <div class="kpi"><div class="kpi-value">{ps.get('project_count', ps.get('active_projects', 0))}</div><div class="kpi-label">AI Projects</div></div>
  <div class="kpi"><div class="kpi-value" style="color:{grade_color}"><span class="grade-box" style="background:{grade_color}">{grade}</span></div><div class="kpi-label">Health Grade</div></div>
  <div class="kpi"><div class="kpi-value">{os_.get('time_to_full_savings_weeks', optim.get('payback_period_weeks', 0))}w</div><div class="kpi-label">Payback Period</div></div>
</div></div></div>

<div class="container">

<section>
  <h2>Executive Summary</h2>
  <div class="callout"><p><strong>{es.get('headline', '')}</strong></p></div>
  <p class="narrative">{es.get('overview_paragraph', '')}</p>
  <div class="callout"><p><strong>Bottom Line:</strong> {es.get('bottom_line', '')}</p></div>
  <h3>Key Findings</h3>
  <ul>
    <li><strong>Finding 1:</strong> {es.get('key_finding_1', '')}</li>
    <li><strong>Finding 2:</strong> {es.get('key_finding_2', '')}</li>
    <li><strong>Finding 3:</strong> {es.get('key_finding_3', '')}</li>
  </ul>
</section>

<section>
  <h2>Current State Analysis</h2>
  <p class="narrative">{csa.get('narrative', '')}</p>
  <p><strong>AI Maturity Level:</strong> {csa.get('maturity_level', 'N/A')} &nbsp;|&nbsp;
     <strong>Health Score:</strong> {csa.get('health_score', 'N/A')}/100 &nbsp;|&nbsp;
     <strong>ROI-Positive Projects:</strong> {pct(cm.get('roi_positive_project_pct', 0))}</p>
</section>

<section>
  <h2>ROI Attribution by Project</h2>
  <p class="narrative">{roi.get('narrative', '')}</p>
  <table><thead><tr><th>Project</th><th>Monthly Cost</th><th>ROI</th><th>Alignment</th><th>Utilization</th><th>Rationale</th></tr></thead>
  <tbody>{proj_rows}</tbody></table>

  <div class="findings">
    <div><h3>🏆 Top Performers</h3><ul>{top_perf}</ul></div>
    <div><h3>⚠️ Underperformers</h3><ul>{under_perf}</ul></div>
  </div>
</section>

<section>
  <h2>Optimization Recommendations</h2>
  <p class="narrative">{optim.get('narrative', '')}</p>
  <h3>Quick Wins</h3>
  <div class="qw-grid">{qw_html}</div>
  <h3>Prioritized Actions</h3>
  <table><thead><tr><th>#</th><th>Action</th><th>Annual Savings</th><th>Effort</th><th>Timeline</th></tr></thead>
  <tbody>{actions_html}</tbody></table>
</section>

<section>
  <h2>Implementation Roadmap</h2>
  <p class="narrative">{roadmap.get('narrative', '')}</p>
  {phase_html}
</section>

<section>
  <h2>Risk & Governance</h2>
  <p class="narrative">{risk.get('narrative', '')}</p>
  <table><thead><tr><th>Risk</th><th>Severity</th><th>Mitigation</th></tr></thead>
  <tbody>{risk_rows}</tbody></table>
</section>

<section>
  <h2>Appendix</h2>
  <p><strong>Methodology:</strong> {appendix.get('methodology_note', '')}</p>
  <p><strong>Data Quality:</strong> {appendix.get('data_quality_note', '')}</p>
  <p><strong>Pricing:</strong> {appendix.get('pricing_assumptions', 'Based on published LLM provider pricing as of February 2026.')}</p>
  <h3>Recommended Next Steps</h3>
  <ol>{"".join(f'<li>{s}</li>' for s in appendix.get('next_steps', []))}</ol>
</section>

</div>

<footer><div class="container">
  <p><strong>ValueOS</strong> · AI ROI Attribution & Cost Optimization · Generated by ValueOS Agentic Analysis Engine v0.1</p>
  <p>This report is confidential and intended for {company_name} executive leadership. &copy; {datetime.now().year} ValueLayer Inc.</p>
</div></footer>

</body></html>"""
