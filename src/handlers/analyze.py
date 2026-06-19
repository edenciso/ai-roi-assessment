"""
ValueOS FDE Demo — Analysis & Report Generation Handler (Async)
"""
import json
import os
import sys
import traceback
import logging
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import boto3
from boto3.dynamodb.conditions import Key

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import at module level so errors surface immediately
from shared.utils import respond, parse_body, get_tenant, get_path_param, new_id, now_iso
from agents.bedrock_analysis import run_full_analysis
from agents.report_renderer import render_html_report

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

PROJECTS_TABLE = os.environ.get("PROJECTS_TABLE")
REPORTS_TABLE = os.environ.get("REPORTS_TABLE")
REPORT_BUCKET = os.environ.get("REPORT_BUCKET")
FUNCTION_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")


def _start_report(event):
    """POST — Create record + trigger async analysis."""
    tenant = get_tenant(event)
    body = parse_body(event)
    ingestion_id = body.get("ingestion_id", "")

    if not ingestion_id:
        return respond(400, {"error": "ingestion_id is required"})

    table = dynamodb.Table(PROJECTS_TABLE)
    summary_resp = table.get_item(Key={"tenant_id": tenant, "project_id": f"SUMMARY#{ingestion_id}"})
    summary = summary_resp.get("Item")
    if not summary:
        return respond(404, {"error": f"Ingestion '{ingestion_id}' not found"})

    report_id = new_id("rpt-")
    reports_table = dynamodb.Table(REPORTS_TABLE)
    reports_table.put_item(Item={
        "tenant_id": tenant,
        "report_id": report_id,
        "ingestion_id": ingestion_id,
        "company_name": summary.get("company", {}).get("name", ""),
        "status": "processing",
        "projects_analyzed": summary.get("project_count", 0),
        "started_at": now_iso(),
    })

    # Invoke self async
    payload = json.dumps({
        "_async_task": "run_analysis",
        "tenant_id": tenant,
        "ingestion_id": ingestion_id,
        "report_id": report_id,
    })
    logger.info(f"Invoking async: function={FUNCTION_NAME}, report={report_id}")
    resp = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="Event",
        Payload=payload,
    )
    logger.info(f"Async invoke response: {resp['StatusCode']}")

    return respond(202, {
        "status": "processing",
        "report_id": report_id,
        "message": f"Analysis started. Poll GET /api/v1/reports/{report_id} for status.",
    })


def _run_analysis_async(event):
    """Background execution — the actual 3-pass analysis."""
    tenant = event["tenant_id"]
    ingestion_id = event["ingestion_id"]
    report_id = event["report_id"]

    logger.info(f"ASYNC START: tenant={tenant}, report={report_id}")

    reports_table = dynamodb.Table(REPORTS_TABLE)
    table = dynamodb.Table(PROJECTS_TABLE)

    try:
        # Load projects
        summary_resp = table.get_item(Key={"tenant_id": tenant, "project_id": f"SUMMARY#{ingestion_id}"})
        summary = summary_resp.get("Item", {})
        company = summary.get("company", {})
        project_ids = summary.get("project_ids", [])
        logger.info(f"Loaded summary: {len(project_ids)} projects")

        projects = []
        for pid in project_ids:
            resp = table.get_item(Key={"tenant_id": tenant, "project_id": pid})
            item = resp.get("Item")
            if item:
                projects.append(item.get("project_data", {}))

        if not projects:
            logger.error("No project data found")
            _update_failed(reports_table, tenant, report_id, "No project data found")
            return

        logger.info(f"Loaded {len(projects)} projects, starting Bedrock analysis...")

        # Run 3-pass analysis
        analysis = run_full_analysis(company, projects)
        logger.info("Bedrock analysis complete, rendering HTML...")

        # Render HTML
        try:
            html = render_html_report(analysis, company)
        except Exception as e:
            logger.error(f"Render error: {e}")
            html = f"<html><body><h1>Render error</h1><pre>{e}</pre></body></html>"

        # Save to S3
        s3_prefix = f"reports/{tenant}/{report_id}"
        s3.put_object(Bucket=REPORT_BUCKET, Key=f"{s3_prefix}/report.html",
                      Body=html.encode("utf-8"), ContentType="text/html", ServerSideEncryption="AES256")
        s3.put_object(Bucket=REPORT_BUCKET, Key=f"{s3_prefix}/analysis.json",
                      Body=json.dumps(analysis, indent=2, default=str).encode("utf-8"),
                      ContentType="application/json", ServerSideEncryption="AES256")
        logger.info("Saved to S3")

        # Update DynamoDB to complete
        exec_summary = analysis.get("pass3_report", {}).get("executive_summary", {})
        opt_summary = analysis.get("pass2_optimization", {}).get("optimization_summary", {})
        report_title = analysis.get("pass3_report", {}).get("report_title",
                                                             f"AI ROI Report — {company.get('name', '')}")

        reports_table.update_item(
            Key={"tenant_id": tenant, "report_id": report_id},
            UpdateExpression="SET #s = :s, title = :t, headline = :h, bottom_line = :bl, "
                             "annual_savings_potential_usd = :sav, savings_pct = :sp, "
                             "health_grade = :hg, s3_html_key = :hk, s3_json_key = :jk, "
                             "model_used = :mu, completed_at = :ca",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "complete",
                ":t": report_title,
                ":h": exec_summary.get("headline", ""),
                ":bl": exec_summary.get("bottom_line", ""),
                ":sav": Decimal(str(opt_summary.get("annual_savings_usd", 0))),
                ":sp": Decimal(str(opt_summary.get("savings_percentage", 0))),
                ":hg": analysis.get("pass3_report", {}).get("current_state_analysis", {}).get("health_grade", ""),
                ":hk": f"{s3_prefix}/report.html",
                ":jk": f"{s3_prefix}/analysis.json",
                ":mu": analysis.get("metadata", {}).get("model", ""),
                ":ca": now_iso(),
            },
        )
        logger.info(f"ASYNC COMPLETE: report={report_id}")

    except Exception as e:
        logger.error(f"ASYNC FAILED: {e}\n{traceback.format_exc()}")
        _update_failed(reports_table, tenant, report_id, str(e))


def _update_failed(reports_table, tenant, report_id, error_msg):
    reports_table.update_item(
        Key={"tenant_id": tenant, "report_id": report_id},
        UpdateExpression="SET #s = :s, #e = :e, failed_at = :fa",
        ExpressionAttributeNames={"#s": "status", "#e": "error"},
        ExpressionAttributeValues={":s": "failed", ":e": error_msg[:500], ":fa": now_iso()},
    )


def _get_report(event):
    """GET /api/v1/reports/{reportId}"""
    tenant = get_tenant(event)
    report_id = get_path_param(event, "reportId")

    table = dynamodb.Table(REPORTS_TABLE)
    resp = table.get_item(Key={"tenant_id": tenant, "report_id": report_id})
    item = resp.get("Item")
    if not item:
        return respond(404, {"error": "Report not found"})

    result = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in item.items()}
    if result.get("status") == "complete":
        result["download"] = f"/api/v1/reports/{report_id}/download"
    return respond(200, result)


def _list_reports(event):
    """GET /api/v1/reports"""
    tenant = get_tenant(event)
    table = dynamodb.Table(REPORTS_TABLE)
    resp = table.query(KeyConditionExpression=Key("tenant_id").eq(tenant), ScanIndexForward=False, Limit=50)
    items = [{k: (float(v) if isinstance(v, Decimal) else v) for k, v in i.items()} for i in resp.get("Items", [])]
    return respond(200, {"reports": items, "count": len(items)})


def handler(event, context):
    logger.info(f"Handler invoked: keys={list(event.keys())}")

    # Async background invocation
    if event.get("_async_task") == "run_analysis":
        logger.info("Detected async task — running analysis")
        _run_analysis_async(event)
        return {"status": "async_complete"}

    # API Gateway request
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    if method == "POST":
        return _start_report(event)
    elif "reportId" in str(event.get("pathParameters", {})):
        return _get_report(event)
    else:
        return _list_reports(event)
