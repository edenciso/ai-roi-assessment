# ValueOS JSON dataset Demo - AI ROI Attribution & Value Assessment (beta)

AWS SAM Serverless deployment workflow for an Autonomous Agentic AI ROI Value Assessment

## One-Line Description

Upload a company's AI project portfolio as JSON → Bedrock Claude Sonnet 4.5 runs a 3-pass agentic analysis → Get a fully detailed, board-ready AI ROI Attribution & Cost Optimization report with recommendations, all in under 60 seconds.

---

## Architecture

```
Client JSON ──→ API Gateway ──→ Ingest Lambda ──→ DynamoDB
                                                     │
FDE triggers ──→ API Gateway ──→ Analyze Lambda ─────┘
                                      │
                                      ├── Pass 1: Cost Attribution Agent (Bedrock Claude)
                                      ├── Pass 2: Optimization Agent (Bedrock Claude)
                                      └── Pass 3: Executive Report Agent (Bedrock Claude)
                                             │
                                             ├── HTML Report ──→ S3
                                             └── Raw JSON   ──→ S3
                                                                 │
FDE downloads ←── API Gateway ←── Download Lambda ←── Presigned URL
```

**No Timestream. No EventBridge schedules. No streaming.**
Just API Gateway → Lambda → DynamoDB → Bedrock → S3.

## AWS Services

| Service | Purpose | Cost at Demo Scale |
|---------|---------|-------------------|
| API Gateway (HTTP) | Request routing | ~$0.01/demo |
| Lambda (Python 3.12) | All compute | ~$0.05/demo |
| DynamoDB (2 tables) | Project + report storage | ~$0.001/demo |
| Bedrock Claude Sonnet 4.5 | 3-pass agentic analysis | ~$0.30/demo |
| S3 | Report storage | ~$0.001/demo |
| Cognito | Auth (optional for demos) | Free tier |
| **Total per demo** | | **~$0.37** |

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- SAM CLI installed (`brew install aws-sam-cli`)
- Bedrock Claude Sonnet 4.5 enabled (Console → Bedrock → Model access)

### Deploy
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh demo us-east-1
```

### Run a Demo (3 commands)

```bash
API="https://xxxxx.execute-api.us-east-1.amazonaws.com/demo"

# 1. Load sample data (or upload client JSON)
curl -s -X POST $API/api/v1/demo/seed \
  -H 'x-tenant-id: demo' | jq .

# 2. Generate the report (paste ingestion_id from step 1)
curl -s -X POST $API/api/v1/reports/generate \
  -H 'Content-Type: application/json' \
  -H 'x-tenant-id: demo' \
  -d '{"ingestion_id": "<PASTE_INGESTION_ID>"}' | jq .

# 3. Get the download link (paste report_id from step 2)
curl -s $API/api/v1/reports/<REPORT_ID>/download \
  -H 'x-tenant-id: demo' | jq .
```

Open the `html_report` URL in a browser — that's your client deliverable.

### Using Real Client Data

Give the client `src/sample_data/input_schema.json` to fill in, then:

```bash
curl -s -X POST $API/api/v1/projects/ingest \
  -H 'Content-Type: application/json' \
  -H 'x-tenant-id: client-name' \
  -d @client_data.json | jq .
```

## Report Contents

The generated report includes:

1. **Executive Summary** — Headline, key findings, bottom line
2. **Current State Analysis** — Health grade, maturity level, critical metrics
3. **ROI Attribution by Project** — ROI scores, utilization, value alignment
4. **Optimization Recommendations** — Quick wins, prioritized actions with $ savings
5. **Implementation Roadmap** — Phased plan with timeline and resource needs
6. **Risk & Governance** — Top risks with severity and mitigation
7. **Appendix** — Methodology, data quality notes, next steps

## Repo Structure

```
valueos-fde/
├── template.yaml           # SAM template (all AWS resources)
├── src/
│   ├── handlers/
│   │   ├── ingest.py       # POST /projects/ingest, GET /projects
│   │   ├── analyze.py      # POST /reports/generate, GET /reports
│   │   ├── download.py     # GET /reports/{id}/download
│   │   └── seed.py         # POST /demo/seed
│   ├── agents/
│   │   ├── bedrock_analysis.py  # 3-pass Claude orchestration
│   │   └── report_renderer.py   # HTML report generator
│   ├── shared/
│   │   └── utils.py        # Pricing engine, helpers
│   └── sample_data/
│       └── input_schema.json    # Client-facing JSON template
├── scripts/
│   └── deploy.sh           # One-command deployment
├── tests/
│   └── test_local.py       # Local smoke tests
└── README.md
```

## Cleanup

```bash
aws cloudformation delete-stack --stack-name valueos-fde-demo
```

## License
Proprietary — ValueLayer. All rights reserved
