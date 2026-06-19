"""
ValueOS FDE Demo — Shared Utilities
Response formatting, tenant isolation, LLM pricing engine, ID generation.
"""
import hashlib, json, os, time, uuid, base64
from datetime import datetime, timezone
from decimal import Decimal

# ─── ID Generation ───
def new_id(prefix=""):
    ts = format(int(time.time() * 1000), "012x")
    rand = uuid.uuid4().hex[:12]
    return f"{prefix}{ts}-{rand}" if prefix else f"{ts}-{rand}"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ─── JSON Helpers ───
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }

def parse_body(event):
    body = event.get("body", "{}")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    return json.loads(body) if body else {}

def parse_qs(event):
    return event.get("queryStringParameters") or {}

def get_path_param(event, name):
    return (event.get("pathParameters") or {}).get(name, "")

# ─── Tenant Extraction (from Cognito JWT or header) ───
def get_tenant(event):
    rc = event.get("requestContext", {})
    claims = rc.get("authorizer", {}).get("jwt", {}).get("claims", {})
    if claims:
        return claims.get("custom:tenant_id", "demo-tenant")
    return (event.get("headers") or {}).get("x-tenant-id", "demo-tenant")

# ═══════════════════════════════════════════════════
# LLM PRICING ENGINE — USD per 1M tokens (Feb 2026)
# Used by the analysis agent to calculate actual costs
# ═══════════════════════════════════════════════════
PRICING = {
    "openai": {
        "gpt-4o":            {"input": 2.50,  "output": 10.00},
        "gpt-4o-mini":       {"input": 0.15,  "output": 0.60},
        "gpt-4-turbo":       {"input": 10.00, "output": 30.00},
        "gpt-4":             {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo":     {"input": 0.50,  "output": 1.50},
        "o1":                {"input": 15.00, "output": 60.00},
        "o1-mini":           {"input": 3.00,  "output": 12.00},
        "o3-mini":           {"input": 1.10,  "output": 4.40},
    },
    "anthropic": {
        "claude-sonnet-4-5": {"input": 3.00,  "output": 15.00},
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-opus-4-5":   {"input": 15.00, "output": 75.00},
        "claude-haiku-3-5":  {"input": 0.80,  "output": 4.00},
        "claude-3-5-sonnet": {"input": 3.00,  "output": 15.00},
        "claude-3-haiku":    {"input": 0.25,  "output": 1.25},
    },
    "google": {
        "gemini-2.0-flash":  {"input": 0.10,  "output": 0.40},
        "gemini-2.0-pro":    {"input": 1.25,  "output": 10.00},
        "gemini-1.5-pro":    {"input": 1.25,  "output": 5.00},
        "gemini-1.5-flash":  {"input": 0.075, "output": 0.30},
    },
    "aws_bedrock": {
        "anthropic.claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "anthropic.claude-3-haiku":    {"input": 0.25, "output": 1.25},
        "amazon.titan-text-express":   {"input": 0.20, "output": 0.60},
        "meta.llama3-1-70b":           {"input": 0.72, "output": 0.72},
        "mistral.mistral-large":       {"input": 4.00, "output": 12.00},
    },
    "azure_openai": {
        "gpt-4o":      {"input": 2.50,  "output": 10.00},
        "gpt-4o-mini": {"input": 0.15,  "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    },
}

def calc_cost(provider, model, input_tokens, output_tokens):
    """Calculate cost in USD for a given LLM call."""
    p = PRICING.get(provider, {}).get(model)
    if not p:
        # Fuzzy match
        for k, v in PRICING.get(provider, {}).items():
            if model.startswith(k):
                p = v
                break
    if not p:
        p = {"input": 5.00, "output": 15.00}  # Conservative default
    ic = (input_tokens / 1_000_000) * p["input"]
    oc = (output_tokens / 1_000_000) * p["output"]
    return round(ic + oc, 6)

def _floats_to_decimals(obj):
    """Recursively convert all floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimals(i) for i in obj]
    return obj

def enrich_projects_with_costs(projects):
    """Add calculated cost fields to each project's usage data."""
    for proj in projects:
        total = 0.0
        for u in proj.get("usage", []):
            c = calc_cost(u.get("provider",""), u.get("model",""),
                          u.get("input_tokens",0), u.get("output_tokens",0))
            u["calculated_cost_usd"] = round(c, 4)
            total += c
        proj["total_calculated_cost_usd"] = round(total, 2)
        # Add cost from subscription fees if present
        for sub in proj.get("subscriptions", []):
            proj["total_calculated_cost_usd"] += sub.get("monthly_cost_usd", 0)
    return _floats_to_decimals(projects)
