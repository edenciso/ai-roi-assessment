"""
ValueOS FDE Demo — Report Download Handler
GET /api/v1/reports/{reportId}/download — Returns presigned S3 URL(s)
"""
import os, sys
import boto3
from boto3.dynamodb.conditions import Key

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.utils import respond, get_tenant, get_path_param

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

REPORTS_TABLE = os.environ.get("REPORTS_TABLE")
REPORT_BUCKET = os.environ.get("REPORT_BUCKET")


def handler(event, context):
    tenant = get_tenant(event)
    report_id = get_path_param(event, "reportId")

    table = dynamodb.Table(REPORTS_TABLE)
    resp = table.get_item(Key={"tenant_id": tenant, "report_id": report_id})
    item = resp.get("Item")
    if not item:
        return respond(404, {"error": "Report not found"})

    # Generate presigned URLs (1 hour expiry)
    urls = {}
    for key_field, label in [("s3_html_key", "html_report"), ("s3_json_key", "raw_analysis")]:
        s3_key = item.get(key_field)
        if s3_key:
            urls[label] = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": REPORT_BUCKET, "Key": s3_key},
                ExpiresIn=3600,
            )

    return respond(200, {
        "report_id": report_id,
        "title": item.get("title", ""),
        "download_urls": urls,
        "expires_in_seconds": 3600,
    })
