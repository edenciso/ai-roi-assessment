"""
ValueOS FDE Demo — Bedrock Claude Agentic Analysis Engine
Three-pass agentic orchestration using AWS Bedrock + Claude Sonnet 4.5:

  Pass 1: COST ATTRIBUTION AGENT
    → Reads raw project data, calculates ROI attribution per project,
      identifies redundancies, scores business value alignment

  Pass 2: OPTIMIZATION AGENT
    → Takes Pass 1 output, generates consolidation recommendations,
      cost reduction roadmap, risk assessment, quick wins

  Pass 3: EXECUTIVE SYNTHESIS AGENT
    → Takes Pass 1 + Pass 2 outputs, generates the final board-ready
      report with executive summary, data tables, recommendations,
      implementation timeline, and ROI projections

This is the Agents SDK orchestration pattern: each pass is a specialized
"agent persona" with its own system prompt, receiving structured input
and producing structured JSON output that feeds the next agent.
"""
import json
import os
import boto3
from decimal import Decimal

def _json(obj, **kwargs):
    """JSON serialize with Decimal support."""
    return json.dumps(obj, default=str, **kwargs)

# Sonnet 4 is significantly faster than Sonnet 4.5 — critical for Lambda timeouts
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _invoke_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4000, model_override: str = None) -> str:
    """Invoke Bedrock Claude with the Anthropic Messages API."""
    model = model_override or BEDROCK_MODEL
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    })
    resp = bedrock.invoke_model(
        modelId=model,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


def _parse_json_response(text: str) -> dict:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = t.find("{")
        end = t.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(t[start:end])
        return {"raw_response": text, "parse_error": True}


# ═══════════════════════════════════════════════════
# PASS 1: COST ATTRIBUTION AGENT
# ═══════════════════════════════════════════════════
def pass1_cost_attribution(company: dict, projects: list) -> dict:
    """Analyze each project's cost structure and attribute ROI."""
    system = """You are the ValueOS Cost Attribution Agent. You are an expert in AI/LLM cost analysis, 
ROI attribution, and enterprise AI portfolio management. Your job is to analyze a company's AI 
project portfolio and produce a rigorous cost attribution analysis.

You MUST respond with ONLY a valid JSON object. No other text."""

    prompt = f"""Analyze this company's AI project portfolio for cost attribution and ROI.

COMPANY PROFILE:
{_json(company, indent=2)}

AI PROJECT PORTFOLIO ({len(projects)} projects):
{_json(projects, indent=2)}

Produce a JSON analysis with this EXACT structure:
{{
  "portfolio_summary": {{
    "total_monthly_llm_cost_usd": number,
    "total_monthly_subscription_cost_usd": number,
    "total_monthly_ai_spend_usd": number,
    "annualized_ai_spend_usd": number,
    "project_count": number,
    "active_projects": number,
    "providers_used": ["list"],
    "models_used": ["list"],
    "total_monthly_tokens": number
  }},
  "project_attributions": [
    {{
      "project_name": "string",
      "department": "string",
      "status": "string",
      "monthly_llm_cost_usd": number,
      "monthly_subscription_cost_usd": number,
      "monthly_total_cost_usd": number,
      "monthly_team_cost_usd": number,
      "cost_per_outcome_unit": number,
      "roi_score": number (0-100, based on KPI achievement vs cost),
      "value_alignment": "high|medium|low" (alignment to business objectives),
      "roi_rationale": "string explaining the ROI score",
      "kpi_achievement_pct": number (0-100),
      "utilization_efficiency": "string (underutilized/optimal/over-provisioned)",
      "risk_level": "low|medium|high|critical"
    }}
  ],
  "cost_by_provider": {{
    "provider_name": {{"monthly_usd": number, "pct_of_total": number, "models": ["list"]}}
  }},
  "cost_by_department": {{
    "department_name": {{"monthly_usd": number, "project_count": number, "avg_roi_score": number}}
  }},
  "redundancy_analysis": {{
    "identified_overlaps": [
      {{
        "tools_involved": ["tool1", "tool2"],
        "overlap_type": "string",
        "estimated_waste_monthly_usd": number,
        "recommendation": "string"
      }}
    ],
    "total_estimated_monthly_waste_usd": number,
    "consolidation_candidates": ["list of project pairs that could merge"]
  }},
  "top_cost_drivers": [
    {{"driver": "string", "monthly_impact_usd": number, "actionable": true/false}}
  ]
}}"""

    raw = _invoke_claude(system, prompt, max_tokens=4000)
    return _parse_json_response(raw)


# ═══════════════════════════════════════════════════
# PASS 2: OPTIMIZATION AGENT
# ═══════════════════════════════════════════════════
def pass2_optimization(company: dict, projects: list, attribution: dict) -> dict:
    """Generate optimization recommendations based on attribution analysis."""
    system = """You are the ValueOS Optimization Agent. You are an expert in AI cost optimization, 
model selection, tool consolidation, and enterprise AI governance. Given a cost attribution 
analysis, you produce concrete, actionable optimization recommendations with quantified savings.

You MUST respond with ONLY a valid JSON object. No other text."""

    prompt = f"""Based on this cost attribution analysis, generate an optimization plan.

COMPANY: {_json(company, indent=2)}

COST ATTRIBUTION (from Analysis Pass 1):
{_json(attribution, indent=2)}

RAW PROJECT DATA:
{_json(projects, indent=2)}

Produce a JSON optimization plan with this EXACT structure:
{{
  "optimization_summary": {{
    "current_monthly_spend_usd": number,
    "optimized_monthly_spend_usd": number,
    "monthly_savings_usd": number,
    "annual_savings_usd": number,
    "savings_percentage": number,
    "implementation_effort": "low|medium|high",
    "time_to_full_savings_weeks": number,
    "confidence_level": "high|medium|low"
  }},
  "quick_wins": [
    {{
      "title": "string",
      "description": "string",
      "monthly_savings_usd": number,
      "effort": "trivial|low|medium",
      "timeline_days": number,
      "action_steps": ["step1", "step2"]
    }}
  ],
  "model_optimization": [
    {{
      "current_model": "provider/model",
      "recommended_model": "provider/model",
      "affected_project": "string",
      "quality_impact": "none|minimal|moderate",
      "monthly_savings_usd": number,
      "rationale": "string"
    }}
  ],
  "consolidation_plan": [
    {{
      "action": "string",
      "tools_affected": ["tool1", "tool2"],
      "replacement": "string",
      "monthly_savings_usd": number,
      "migration_effort_days": number,
      "risk": "low|medium|high"
    }}
  ],
  "governance_recommendations": [
    {{
      "area": "string (e.g. shadow AI, cost controls, approval workflows)",
      "current_state": "string",
      "recommended_state": "string",
      "priority": "immediate|short-term|medium-term",
      "business_impact": "string"
    }}
  ],
  "implementation_roadmap": {{
    "week_1_2": [
      {{"action": "string", "owner": "string", "savings_usd": number}}
    ],
    "week_3_4": [
      {{"action": "string", "owner": "string", "savings_usd": number}}
    ],
    "month_2_3": [
      {{"action": "string", "owner": "string", "savings_usd": number}}
    ]
  }},
  "risk_assessment": [
    {{"risk": "string", "probability": "low|medium|high", "impact": "string", "mitigation": "string"}}
  ]
}}"""

    raw = _invoke_claude(system, prompt, max_tokens=4000)
    return _parse_json_response(raw)


# ═══════════════════════════════════════════════════
# PASS 3: EXECUTIVE SYNTHESIS AGENT
# ═══════════════════════════════════════════════════
def pass3_executive_report(company: dict, attribution: dict, optimization: dict) -> dict:
    """Synthesize the final executive report from all analysis passes."""
    system = """You are the ValueOS Executive Report Agent. You synthesize cost attribution and 
optimization analyses into a polished, board-ready executive report. Your output will be 
rendered directly as a client deliverable. Write with authority, specificity, and clarity.

You MUST respond with ONLY a valid JSON object. No other text."""

    prompt = f"""Synthesize this analysis into a complete executive report.

COMPANY: {_json(company, indent=2)}

COST ATTRIBUTION (Pass 1):
{_json(attribution, indent=2)}

OPTIMIZATION PLAN (Pass 2):
{_json(optimization, indent=2)}

Produce a JSON executive report with this EXACT structure:
{{
  "report_title": "AI ROI Attribution & Cost Optimization Report — [Company Name]",
  "generated_date": "YYYY-MM-DD",
  "executive_summary": {{
    "headline": "One compelling headline (max 15 words)",
    "overview_paragraph": "3-4 sentences summarizing the entire analysis with specific numbers. Board-ready tone.",
    "key_finding_1": "string — most important finding with numbers",
    "key_finding_2": "string — second most important finding",
    "key_finding_3": "string — third finding",
    "bottom_line": "One sentence: the single most important takeaway for the C-suite"
  }},
  "current_state_analysis": {{
    "narrative": "2-3 paragraphs describing the current AI portfolio state. Professional, specific, data-driven.",
    "health_score": number (0-100),
    "health_grade": "A|B|C|D|F",
    "maturity_level": "Ad-hoc|Emerging|Defined|Managed|Optimized",
    "critical_metrics": {{
      "total_annual_ai_spend": number,
      "cost_per_employee_monthly": number,
      "ai_tools_per_department_avg": number,
      "utilization_rate_avg_pct": number,
      "roi_positive_project_pct": number,
      "shadow_ai_risk_level": "low|medium|high"
    }}
  }},
  "roi_attribution_detail": {{
    "narrative": "2 paragraphs explaining how ROI was calculated and attributed.",
    "top_performers": [
      {{"project": "string", "roi_score": number, "why": "string"}}
    ],
    "underperformers": [
      {{"project": "string", "roi_score": number, "issue": "string", "recommendation": "string"}}
    ],
    "unattributable_spend_pct": number,
    "attribution_confidence": "high|medium|low"
  }},
  "optimization_recommendations": {{
    "narrative": "2 paragraphs framing the optimization opportunity.",
    "total_annual_savings_potential_usd": number,
    "savings_as_pct_of_spend": number,
    "payback_period_weeks": number,
    "prioritized_actions": [
      {{
        "priority": 1,
        "title": "string",
        "description": "string",
        "annual_savings_usd": number,
        "effort": "low|medium|high",
        "timeline": "string"
      }}
    ]
  }},
  "implementation_roadmap": {{
    "narrative": "1-2 paragraphs describing the phased approach.",
    "phases": [
      {{
        "phase": "string (e.g. Weeks 1-2: Quick Wins)",
        "actions": ["string"],
        "expected_savings_usd": number,
        "resources_needed": "string"
      }}
    ]
  }},
  "risk_and_governance": {{
    "narrative": "1-2 paragraphs on governance gaps and risk posture.",
    "top_risks": [
      {{"risk": "string", "severity": "high|medium|low", "mitigation": "string"}}
    ]
  }},
  "appendix": {{
    "methodology_note": "2-3 sentences on how this analysis was conducted.",
    "data_quality_note": "1-2 sentences on data completeness and confidence.",
    "pricing_assumptions": "Note on LLM pricing data used (Feb 2026 rates).",
    "next_steps": ["string — concrete next step 1", "string — next step 2", "string — next step 3"]
  }}
}}"""

    raw = _invoke_claude(system, prompt, max_tokens=4000)
    return _parse_json_response(raw)


# ═══════════════════════════════════════════════════
# ORCHESTRATOR — Runs all three passes
# ═══════════════════════════════════════════════════
def run_full_analysis(company: dict, projects: list) -> dict:
    """Execute the three-pass agentic analysis pipeline.
    
    Returns the complete analysis bundle:
    {
        "pass1_attribution": { ... },
        "pass2_optimization": { ... },
        "pass3_report": { ... },
        "metadata": { "model": ..., "passes": 3, "total_tokens_est": ... }
    }
    """
    # Pass 1: Cost Attribution
    attribution = pass1_cost_attribution(company, projects)

    # Pass 2: Optimization (uses Pass 1 output)
    optimization = pass2_optimization(company, projects, attribution)

    # Pass 3: Executive Report (uses Pass 1 + Pass 2)
    report = pass3_executive_report(company, attribution, optimization)

    return {
        "pass1_attribution": attribution,
        "pass2_optimization": optimization,
        "pass3_report": report,
        "metadata": {
            "model": BEDROCK_MODEL,
            "passes_completed": 3,
            "analysis_engine": "ValueOS Agentic Orchestration v0.1",
        }
    }
