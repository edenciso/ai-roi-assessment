"""
ValueOS FDE Demo — Seed Data Handler
POST /api/v1/demo/seed — Load realistic sample AI portfolio data

The FDE calls this endpoint to instantly populate a demo tenant with
realistic AI project data for a live demo. No file upload needed —
just POST and go.
"""
import json
import os
import sys
from decimal import Decimal

import boto3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.utils import respond, get_tenant, new_id, now_iso, enrich_projects_with_costs, _floats_to_decimals

dynamodb = boto3.resource("dynamodb")
TABLE = os.environ.get("PROJECTS_TABLE")

SAMPLE_DATA = {
    "company": {
        "name": "Nexus Digital Solutions",
        "industry": "B2B SaaS",
        "size": "200-1000",
        "annual_revenue_usd": 45000000,
        "ai_budget_annual_usd": 840000,
    },
    "projects": [
        {
            "name": "Customer Support AI Copilot",
            "department": "Customer Success",
            "status": "active",
            "owner": "VP Customer Success",
            "description": "AI-powered agent handling tier-1 support tickets, suggesting responses to agents, auto-resolving password resets and FAQ queries",
            "business_objective": "Reduce average resolution time by 40% and handle 60% of tier-1 tickets autonomously",
            "start_date": "2025-06-15",
            "kpis": [
                {"name": "Avg Resolution Time", "baseline": 24, "current": 11, "target": 14, "unit": "hours"},
                {"name": "Autonomous Resolution Rate", "baseline": 0, "current": 52, "target": 60, "unit": "percent"},
                {"name": "CSAT Score", "baseline": 3.8, "current": 4.3, "target": 4.5, "unit": "out of 5"},
                {"name": "Cost per Ticket", "baseline": 18.50, "current": 8.20, "target": 10, "unit": "USD"}
            ],
            "usage": [
                {"provider": "openai", "model": "gpt-4o", "monthly_calls": 45000, "avg_input_tokens": 1200, "avg_output_tokens": 600},
                {"provider": "openai", "model": "gpt-4o-mini", "monthly_calls": 120000, "avg_input_tokens": 800, "avg_output_tokens": 400},
                {"provider": "openai", "model": "text-embedding-3-small", "monthly_calls": 200000, "avg_input_tokens": 500, "avg_output_tokens": 0}
            ],
            "subscriptions": [
                {"tool": "Intercom AI", "monthly_cost_usd": 2400, "seats": 30, "utilization_pct": 85},
                {"tool": "Zendesk AI Add-on", "monthly_cost_usd": 1800, "seats": 30, "utilization_pct": 35}
            ],
            "team": {"headcount": 3, "hours_per_week": 20, "avg_hourly_cost_usd": 75},
            "risks": ["Hallucination in sensitive customer responses", "Overlap between Intercom AI and custom GPT-4o pipeline"],
            "redundancies": ["Intercom AI and Zendesk AI both do ticket classification", "GPT-4o used for tasks that gpt-4o-mini could handle"]
        },
        {
            "name": "Sales Intelligence Pipeline",
            "department": "Sales",
            "status": "active",
            "owner": "CRO",
            "description": "AI system that enriches leads, generates personalized outreach, scores deals, and provides call coaching summaries",
            "business_objective": "Increase qualified pipeline by 30% and improve win rate by 10%",
            "start_date": "2025-08-01",
            "kpis": [
                {"name": "Qualified Pipeline", "baseline": 8000000, "current": 9800000, "target": 10400000, "unit": "USD/quarter"},
                {"name": "Win Rate", "baseline": 22, "current": 25, "target": 24, "unit": "percent"},
                {"name": "Lead Response Time", "baseline": 4.2, "current": 0.8, "target": 1, "unit": "hours"},
                {"name": "Outreach Reply Rate", "baseline": 3.5, "current": 7.2, "target": 6, "unit": "percent"}
            ],
            "usage": [
                {"provider": "anthropic", "model": "claude-sonnet-4-5", "monthly_calls": 15000, "avg_input_tokens": 3000, "avg_output_tokens": 1500},
                {"provider": "openai", "model": "gpt-4o", "monthly_calls": 30000, "avg_input_tokens": 2000, "avg_output_tokens": 1000}
            ],
            "subscriptions": [
                {"tool": "Apollo.io", "monthly_cost_usd": 800, "seats": 15, "utilization_pct": 90},
                {"tool": "Gong AI", "monthly_cost_usd": 3200, "seats": 15, "utilization_pct": 70},
                {"tool": "Clay", "monthly_cost_usd": 500, "seats": 5, "utilization_pct": 60},
                {"tool": "Lavender AI", "monthly_cost_usd": 450, "seats": 15, "utilization_pct": 25}
            ],
            "team": {"headcount": 2, "hours_per_week": 15, "avg_hourly_cost_usd": 85},
            "risks": ["Dual-spending on similar LLM calls (Claude for analysis, GPT-4o for generation)", "Lavender AI barely used"],
            "redundancies": ["Claude and GPT-4o doing similar email generation tasks", "Lavender AI overlaps with custom outreach pipeline"]
        },
        {
            "name": "Content Generation Engine",
            "department": "Marketing",
            "status": "active",
            "owner": "VP Marketing",
            "description": "Automated blog posts, social media content, email campaigns, and landing page copy generation",
            "business_objective": "3x content output while maintaining quality and reducing agency spend by 50%",
            "start_date": "2025-04-01",
            "kpis": [
                {"name": "Content Pieces / Month", "baseline": 12, "current": 38, "target": 36, "unit": "pieces"},
                {"name": "Agency Spend", "baseline": 25000, "current": 10000, "target": 12500, "unit": "USD/month"},
                {"name": "Organic Traffic", "baseline": 45000, "current": 62000, "target": 60000, "unit": "monthly visitors"},
                {"name": "Content Quality Score", "baseline": 7.5, "current": 7.8, "target": 8, "unit": "out of 10"}
            ],
            "usage": [
                {"provider": "anthropic", "model": "claude-sonnet-4-5", "monthly_calls": 8000, "avg_input_tokens": 2500, "avg_output_tokens": 3000},
                {"provider": "openai", "model": "gpt-4o", "monthly_calls": 5000, "avg_input_tokens": 1500, "avg_output_tokens": 2000}
            ],
            "subscriptions": [
                {"tool": "Jasper AI", "monthly_cost_usd": 1200, "seats": 8, "utilization_pct": 40},
                {"tool": "Surfer SEO", "monthly_cost_usd": 200, "seats": 3, "utilization_pct": 80},
                {"tool": "Canva AI", "monthly_cost_usd": 130, "seats": 8, "utilization_pct": 75}
            ],
            "team": {"headcount": 2, "hours_per_week": 25, "avg_hourly_cost_usd": 65},
            "risks": ["Jasper AI underutilized — team prefers custom Claude pipeline", "Brand voice inconsistency across tools"],
            "redundancies": ["Jasper AI overlaps almost entirely with custom Claude pipeline", "GPT-4o and Claude doing same content tasks"]
        },
        {
            "name": "Internal Knowledge Assistant",
            "department": "Engineering",
            "status": "active",
            "owner": "VP Engineering",
            "description": "RAG-based chatbot over internal docs, Confluence, Slack history — answers engineering questions, onboards new hires",
            "business_objective": "Reduce onboarding time by 50% and cut internal question load on senior engineers by 40%",
            "start_date": "2025-09-01",
            "kpis": [
                {"name": "Onboarding Time", "baseline": 6, "current": 4.5, "target": 3, "unit": "weeks"},
                {"name": "Questions to Sr Engineers", "baseline": 45, "current": 30, "target": 27, "unit": "per week"},
                {"name": "Knowledge Base Coverage", "baseline": 0, "current": 65, "target": 85, "unit": "percent"},
                {"name": "Answer Accuracy", "baseline": 0, "current": 78, "target": 90, "unit": "percent"}
            ],
            "usage": [
                {"provider": "aws_bedrock", "model": "anthropic.claude-3-5-sonnet", "monthly_calls": 20000, "avg_input_tokens": 4000, "avg_output_tokens": 800},
                {"provider": "aws_bedrock", "model": "amazon.titan-text-express", "monthly_calls": 50000, "avg_input_tokens": 200, "avg_output_tokens": 0}
            ],
            "subscriptions": [
                {"tool": "Pinecone", "monthly_cost_usd": 700, "seats": 1, "utilization_pct": 55},
                {"tool": "Notion AI", "monthly_cost_usd": 960, "seats": 80, "utilization_pct": 30}
            ],
            "team": {"headcount": 2, "hours_per_week": 30, "avg_hourly_cost_usd": 95},
            "risks": ["Answer accuracy below target — RAG pipeline needs tuning", "Notion AI adoption very low"],
            "redundancies": ["Notion AI barely used — team prefers custom RAG chatbot"]
        },
        {
            "name": "Code Review Automation",
            "department": "Engineering",
            "status": "pilot",
            "owner": "Engineering Manager",
            "description": "AI-powered code review that catches bugs, suggests improvements, and enforces coding standards before human review",
            "business_objective": "Reduce code review cycle time by 60% and catch 80% of common issues before human review",
            "start_date": "2025-11-15",
            "kpis": [
                {"name": "Review Cycle Time", "baseline": 18, "current": 12, "target": 7, "unit": "hours"},
                {"name": "Bugs Caught Pre-Review", "baseline": 15, "current": 45, "target": 65, "unit": "percent"},
                {"name": "Developer Satisfaction", "baseline": 3.2, "current": 3.8, "target": 4, "unit": "out of 5"}
            ],
            "usage": [
                {"provider": "anthropic", "model": "claude-sonnet-4-5", "monthly_calls": 6000, "avg_input_tokens": 8000, "avg_output_tokens": 2000}
            ],
            "subscriptions": [
                {"tool": "GitHub Copilot", "monthly_cost_usd": 1900, "seats": 50, "utilization_pct": 70},
                {"tool": "Codacy", "monthly_cost_usd": 600, "seats": 50, "utilization_pct": 45}
            ],
            "team": {"headcount": 1, "hours_per_week": 10, "avg_hourly_cost_usd": 95},
            "risks": ["Pilot stage — unclear if Codacy adds value on top of Claude review"],
            "redundancies": ["Codacy static analysis overlaps with Claude code review capabilities"]
        },
        {
            "name": "Financial Forecasting Assistant",
            "department": "Finance",
            "status": "planned",
            "owner": "CFO",
            "description": "AI agent that assists with revenue forecasting, expense analysis, and board report preparation",
            "business_objective": "Reduce forecast preparation time by 70% and improve forecast accuracy by 15%",
            "start_date": "2026-03-01",
            "kpis": [
                {"name": "Forecast Prep Time", "baseline": 40, "current": 40, "target": 12, "unit": "hours/quarter"},
                {"name": "Forecast Accuracy", "baseline": 82, "current": 82, "target": 94, "unit": "percent"}
            ],
            "usage": [],
            "subscriptions": [
                {"tool": "Runway FP&A", "monthly_cost_usd": 1500, "seats": 3, "utilization_pct": 0}
            ],
            "team": {"headcount": 1, "hours_per_week": 5, "avg_hourly_cost_usd": 100},
            "risks": ["Not yet started — Runway subscription running without usage"],
            "redundancies": []
        }
    ]
}


def handler(event, context):
    """POST /api/v1/demo/seed — Load sample data for live demo."""
    tenant = get_tenant(event)
    table = dynamodb.Table(TABLE)

    data = SAMPLE_DATA.copy()
    projects = enrich_projects_with_costs(data["projects"])
    company = _floats_to_decimals(data["company"])

    ingestion_id = new_id("ing-")
    project_ids = []

    for proj in projects:
        pid = new_id("proj-")
        project_ids.append(pid)
        table.put_item(Item={
            "tenant_id": tenant,
            "project_id": pid,
            "ingestion_id": ingestion_id,
            "company": company,
            "project_data": proj,
            "ingested_at": now_iso(),
        })

    total_cost = sum(float(p.get("total_calculated_cost_usd", 0)) for p in projects)
    table.put_item(Item={
        "tenant_id": tenant,
        "project_id": f"SUMMARY#{ingestion_id}",
        "ingestion_id": ingestion_id,
        "company": company,
        "project_count": len(projects),
        "total_monthly_ai_cost_usd": Decimal(str(round(total_cost, 2))),
        "project_ids": project_ids,
        "ingested_at": now_iso(),
    })

    return respond(201, {
        "status": "demo_data_loaded",
        "company": data["company"]["name"],
        "ingestion_id": ingestion_id,
        "projects_loaded": len(projects),
        "total_monthly_ai_cost_usd": round(total_cost, 2),
        "next_step": f'POST /api/v1/reports/generate with {{"ingestion_id": "{ingestion_id}"}}',
    })
