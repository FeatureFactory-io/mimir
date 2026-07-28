# Design & Deploy Cloud Infra

**Playbook**: Edda v55.0 (Released)
**Workflow ID**: 12
**Description**: Design and deploy cloud infrastructure using AWS CDK with Python. Supports two deployment styles chosen in DCI-01: **Kubernetes/EKS** (separate infra repo, weighted Route53) or **Elastic Beanstalk** (monorepo or separate repo, EB CNAME swap). Establish Makefile targets for infra operations and GitHub Actions for CDK deploy. Blue/green switching is style-specific: Route53 weights (EKS) or EB swap-environment-cnames (EB).
**Phase Organization**: Uses phases
**Total Activities**: 7
**Export Date**: 2026-07-27 10:52 UTC

## Activities

See individual activity files in this directory.

## Editing Instructions

- **Add activity**: Create new file with pattern PREFIX-XX-Name.md
- **Remove activity**: Delete the .md file
- **Reorder**: Rename files to change order numbers
- **Edit content**: Modify description, guidance, dependencies
- **Change phase**: Update the Phase field

After editing, use import_workflow_from_local MCP tool to import changes.
