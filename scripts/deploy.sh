#!/bin/bash
# ═══════════════════════════════════════════════════
# ValueOS FDE Demo — One-Command Deploy
# ═══════════════════════════════════════════════════
set -euo pipefail

STAGE="${1:-demo}"
REGION="${2:-us-east-1}"
STACK="valueos-fde-${STAGE}"

echo "╔══════════════════════════════════════════════╗"
echo "║  ValueOS FDE Demo — Deploy                   ║"
echo "║  Stage: ${STAGE}  |  Region: ${REGION}            ║"
echo "╚══════════════════════════════════════════════╝"

# Preflight
command -v aws >/dev/null || { echo "✗ AWS CLI missing"; exit 1; }
command -v sam >/dev/null || { echo "✗ SAM CLI missing"; exit 1; }

echo ""
echo "→ Verifying Bedrock Claude Sonnet 4.5 access..."
aws bedrock list-foundation-models --region "${REGION}" \
  --query "modelSummaries[?modelId=='anthropic.claude-sonnet-4-5-20250514-v1:0'].modelId" \
  --output text 2>/dev/null | grep -q "claude" && echo "  ✓ Bedrock model available" || \
  echo "  ⚠ Enable Claude Sonnet 4.5 in Bedrock console → Model access"

echo ""
echo "→ Building..."
sam build --template-file template.yaml --use-container --parallel 2>/dev/null || \
sam build --template-file template.yaml

echo ""
echo "→ Deploying..."
sam deploy \
  --stack-name "${STACK}" \
  --region "${REGION}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Stage="${STAGE}" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --resolve-s3

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Deployment Complete!                        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

API=$(aws cloudformation describe-stacks --stack-name "${STACK}" --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

echo "API URL: ${API}"
echo ""
echo "Quick Start (no auth for demo):"
echo ""
echo "  # 1. Load sample data"
echo "  curl -X POST ${API}/api/v1/demo/seed -H 'x-tenant-id: demo'"
echo ""
echo "  # 2. Generate report (copy ingestion_id from step 1)"
echo '  curl -X POST ${API}/api/v1/reports/generate \'
echo "    -H 'Content-Type: application/json' -H 'x-tenant-id: demo' \\"
echo "    -d '{\"ingestion_id\": \"<INGESTION_ID>\"}'"
echo ""
echo "  # 3. Download report (copy report_id from step 2)"
echo "  curl ${API}/api/v1/reports/<REPORT_ID>/download -H 'x-tenant-id: demo'"
