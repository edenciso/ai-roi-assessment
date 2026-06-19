"""
ValueOS FDE Demo — Project Data Ingestion Handler
POST /api/v1/projects/ingest  — Upload client AI project JSON (single or batch)
GET  /api/v1/projects         — List ingested projects for tenant

The FDE uploads the client's AI project data as JSON. The schema supports:
- AI tool inventory with usage telemetry
- Subscription costs
- Team allocation and productivity metrics
- Business outcome KPIs
- Redundancy and overlap annotations

No Timestream, no streaming — pure API Gateway → Lambda → DynamoDB.
"""
import json
import os
import sys

import boto3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.utils import respond, parse_body, parse_qs, get_tenant, new_id, now_iso, enrich_projects_with_costs, _floats_to_decimals

dynamodb = boto3.resource("dynamodb")
TABLE = os.environ.get("PROJECTS_TABLE", "valueos-fde-demo-projects")

# ═══════════════════════════════════════════════════
# INPUT SCHEMA DEFINITION
# This is the JSON contract the FDE uses with client data.
# ═══════════════════════════════════════════════════
SCHEMA_EXAMPLE = {
    "company": {
        "name": "string — company name",
        "industry": "string — e.g. fintech, healthtech, saas",
        "size": "string — e.g. 50-200, 200-1000, 1000-5000",
        "annual_revenue_usd": "number — optional",
        "ai_budget_annual_usd": "number — total AI spend budget",
    },
    "projects": [
        {
            "name": "string — project name",
            "department": "string — e.g. engineering, marketing, sales, support",
            "status": "string — active|pilot|planned|deprecated",
            "owner": "string — team or person name",
            "description": "string — what this AI project does",
            "business_objective": "string — what business outcome it targets",
            "start_date": "YYYY-MM-DD",
            "kpis": [
                {"name": "string", "baseline": "number", "current": "number", "target": "number", "unit": "string"}
            ],
            "usage": [
                {
                    "provider": "openai|anthropic|google|aws_bedrock|azure_openai",
                    "model": "string — model identifier",
                    "monthly_calls": "number",
                    "avg_input_tokens": "number",
                    "avg_output_tokens": "number",
                    "input_tokens": "number — total input tokens/month (computed if missing)",
                    "output_tokens": "number — total output tokens/month (computed if missing)",
                }
            ],
            "subscriptions": [
                {"tool": "string", "monthly_cost_usd": "number", "seats": "number", "utilization_pct": "number"}
            ],
            "team": {
                "headcount": "number",
                "hours_per_week": "number — hours spent on this project",
                "avg_hourly_cost_usd": "number — fully loaded"
            },
            "risks": ["string — known risks or concerns"],
            "redundancies": ["string — overlapping tools or capabilities"],
        }
    ]
}


def _validate_and_normalize(data):
    """Validate input JSON and normalize computed fields."""
    errors = []
    company = data.get("company", {})
    if not company.get("name"):
        errors.append("company.name is required")

    projects = data.get("projects", [])
    if not projects:
        errors.append("At least one project is required")

    for i, p in enumerate(projects):
        if not p.get("name"):
            errors.append(f"projects[{i}].name is required")
        # Normalize usage: compute total tokens from monthly_calls * avg if not provided
        for u in p.get("usage", []):
            if not u.get("input_tokens") and u.get("monthly_calls") and u.get("avg_input_tokens"):
                u["input_tokens"] = u["monthly_calls"] * u["avg_input_tokens"]
            if not u.get("output_tokens") and u.get("monthly_calls") and u.get("avg_output_tokens"):
                u["output_tokens"] = u["monthly_calls"] * u["avg_output_tokens"]
            u.setdefault("input_tokens", 0)
            u.setdefault("output_tokens", 0)

    return errors


def _ingest(event):
    """POST /api/v1/projects/ingest"""
    tenant = get_tenant(event)
    body = parse_body(event)

    errors = _validate_and_normalize(body)
    if errors:
        return respond(400, {"error": "Validation failed", "details": errors,
                             "schema_example": SCHEMA_EXAMPLE})

    # Enrich with calculated LLM costs
    projects = enrich_projects_with_costs(body.get("projects", []))
    company = _floats_to_decimals(body.get("company", {}))

    # Store each project as a separate DynamoDB item (enables per-project queries)
    table = dynamodb.Table(TABLE)
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

    # Also store the full company context as a summary record
    from decimal import Decimal
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
        "status": "ingested",
        "ingestion_id": ingestion_id,
        "projects_processed": len(projects),
        "total_monthly_ai_cost_usd": round(total_cost, 2),
        "project_ids": project_ids,
        "next_step": "POST /api/v1/reports/generate with {\"ingestion_id\": \"" + ingestion_id + "\"}",
    })


def _list(event):
    """GET /api/v1/projects"""
    tenant = get_tenant(event)
    table = dynamodb.Table(TABLE)
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("tenant_id").eq(tenant),
        ScanIndexForward=False,
        Limit=100,
    )
    items = resp.get("Items", [])
    # Return summaries only
    summaries = [i for i in items if str(i.get("project_id", "")).startswith("SUMMARY#")]
    return respond(200, {"tenant_id": tenant, "ingestions": summaries, "count": len(summaries)})


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if method == "POST":
        return _ingest(event)
    return _list(event)
