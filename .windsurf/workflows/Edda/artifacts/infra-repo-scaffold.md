# Artifact: Infra Repo Scaffold

**Workflow**: DCI — Design & Deploy Cloud Infra
**Purpose**: Reference directory structure for the infrastructure repository

## Repository Structure

```
{project}-infra/
├── app.py                          ← CDK entry point (imports and wires stacks)
├── cdk.json                        ← CDK config (account, region, context)
├── requirements.txt                ← Python deps: aws-cdk-lib, constructs, boto3, pytest
├── Makefile                        ← Infra operations (deploy, destroy, traffic-switch, etc.)
├── README.md                       ← Quick start, architecture overview, make targets
├── .github/
│   └── workflows/
│       └── infra.yml               ← GH Actions: deploy on push, manual switch/rollback
├── stacks/
│   ├── __init__.py
│   ├── vpc_stack.py                ← VPC, subnets, NAT Gateway, security groups
│   ├── eks_stack.py                ← EKS cluster, node group, ECR repo, namespaces
│   └── dns_stack.py                ← Route53 hosted zone, prod/idle DNS records
├── scripts/
│   └── traffic_switch.py           ← DNS weight switcher (switch/rollback/status)
├── tests/
│   ├── __init__.py
│   ├── test_vpc_stack.py           ← CDK snapshot/assertion tests for VPC
│   ├── test_eks_stack.py           ← CDK tests for EKS + ECR
│   └── test_dns_stack.py           ← CDK tests for Route53
├── cdk.out/                        ← (gitignored) synthesized CloudFormation templates
└── .traffic_state.json             ← (gitignored) last known traffic state for rollback
```

## Key Files

### app.py

CDK entry point that imports all stacks and wires dependencies:
- VpcStack (no dependencies)
- EksStack (depends on VpcStack.vpc)
- DnsStack (no stack dependencies, but logically follows EKS)

### Makefile Targets

```
make help             — Show all targets
make provision        — Install CDK + Python deps
make synth            — Synthesize CloudFormation (dry run)
make deploy           — Deploy all stacks
make destroy          — Destroy all stacks (DANGEROUS)
make status           — Show stack status
make traffic-switch   — Swap prod/idle DNS
make traffic-rollback — Revert last switch
make traffic-status   — Show current routing
make test             — Run CDK tests
```

### .gitignore Additions

```
cdk.out/
.traffic_state.json
.venv/
__pycache__/
*.pyc
```

## Conventions

- Stack names: `{Project}VpcStack`, `{Project}EksStack`, `{Project}DnsStack`
- All AWS resources tagged with `project={project}`, `environment=shared`, `managed-by=cdk`
- CDK context for environment-specific values (account, region, domain)
- Tests use CDK assertions (Template.from_stack)

