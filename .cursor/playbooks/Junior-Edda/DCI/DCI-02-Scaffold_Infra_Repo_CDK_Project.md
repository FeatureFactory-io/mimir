# Activity: Scaffold Infra Repo & CDK Project

**Activity ID**: 75
**Order**: 2
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 74 (Review SAO & Define Infra Requirements)

## Description

Scaffold Infra Repo & CDK Project

## Guidance

# Scaffold Infra Repo & CDK Project

## Objective

Create an AWS CDK Python project with Makefile for infra operations and a GitHub Actions workflow placeholder. Layout depends on deployment style from DCI-01.

---

## Process

### Path Selection

Refer to `docs/architecture/INFRA_REQUIREMENTS.md` § Deployment Style.

| Style | Repo layout |
|-------|-------------|
| **EKS** | Separate `{project}-infra` repository (recommended) |
| **Elastic Beanstalk** | `{project}-infra/` **or** `infra/` inside the application monorepo |

> **Monorepo note (EB):** Small teams often keep `infra/` in the app repo. CDK deploy and app CI/CD share secrets via `infra/.env`. Separate repo still valid for larger orgs.

---

## EKS Path

### 1. Create Infra Repository

```bash
mkdir {project}-infra && cd {project}-infra && git init
```

### 2. Initialize CDK Project

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install aws-cdk-lib constructs
mkdir -p stacks tests
```

Create `app.py` wiring `VpcStack`, `EksStack`, `DnsStack`.

### 3. Directory Structure

```
{project}-infra/
├── app.py
├── cdk.json
├── requirements.txt
├── Makefile
├── .github/workflows/infra.yml
├── stacks/
│   ├── vpc_stack.py
│   ├── eks_stack.py
│   └── dns_stack.py
├── scripts/traffic_switch.py
└── tests/test_stacks.py
```

---

## Elastic Beanstalk Path

### 1. Create `infra/` Directory

In app monorepo (or separate repo):

```bash
mkdir -p infra/stacks infra/scripts infra/tests infra/lambda
```

### 2. Initialize CDK Project

Same venv/CDK setup as EKS path.

Create `app.py` wiring stacks for your project, e.g.:

- `MimirNetwork` — VPC lookup, EB security group, RDS ingress
- `MimirApp` — EB app, `{project}-prod` / `{project}-idle`, ECR ref, CI IAM, alarms
- `MimirBackups` — S3 pre-migrate bucket, SSM on EB instance role
- `MimirSes` — SES configuration set (if transactional email)
- `MimirDns` — Route53 CNAME → `{project}-prod.eba-…` (see DCI-05 EB path)

### 3. Directory Structure

```
infra/
├── app.py
├── cdk.json
├── requirements.txt
├── .env.example          ← secrets template (gitignored .env)
├── eb_live_platform_settings.json  ← exported from live EB (no secrets)
├── stacks/
│   ├── network_stack.py
│   ├── app_stack.py      ← EB + ECR + CI IAM
│   ├── backups_stack.py
│   ├── ses_stack.py
│   └── dns_stack.py
├── scripts/
│   ├── export_eb_live_settings.py
│   └── diff_eb_live_vs_cdk.py
├── lambda/route53_cname/ ← idempotent CNAME UPSERT
└── tests/test_stacks.py
```

### 4. Two Sources of Truth (EB)

| What | Where |
|------|--------|
| Platform settings (VPC, ALB, instance type, non-secret env vars) | `eb_live_platform_settings.json` — refresh after console changes |
| Secrets (`DATABASE_URL`, `DJANGO_SECRET_KEY`, etc.) | `infra/.env` at `cdk deploy` — never committed |

See **AWS CDK with Python** skill § EB Platform Settings Export.

---

## Infra Makefile (Both Paths)

```makefile
.PHONY: help synth deploy destroy status test provision

help: ## Show help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

synth: ## Synthesize CDK stacks
	cdk synth

deploy: ## Deploy all stacks
	cdk deploy --all --require-approval never

test: ## Run CDK tests
	python -m pytest tests/ -v

provision: ## Install CDK deps
	pip install -r requirements.txt
```

EB monorepo: add `##@ Deploy` targets to the **app** Makefile (`swap`, `eb-status`, `backup`) — see EB skill.

---

## Deliverables

- ✅ CDK project initialized with stack placeholders for chosen style
- ✅ Infra Makefile with synth/deploy/test targets
- ✅ EB: `.env.example` + export/diff scripts scaffolded
- ✅ Committed

## Agent

None

## Skill

**Title**: AWS CDK with Python
**Capability Domain**: INFRASTRUCTURE_AS_CODE
**Technology Stack**: AWS CDK + Python

## Rules

None

## Artifacts Produced

- **Infra Repo Scaffold** (Template) - Required

## Artifacts Consumed

- **INFRA Requirements (EB Reference)** (Document) - Required

## Notes

No additional notes.
