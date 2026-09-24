# Bug #186: workflow order through released-playbook PIPs

## A. Context map
- `methodology/services/pip_service.py`: validate and persist typed draft changes.
- `methodology/services/pip_apply_changes_service.py`: shared dry-run/finalization apply path.
- `methodology/api/viewsets_resources.py`, `serializers.py`: hosted MCP write/read boundary.
- `mcp_integration/facade/tools_http.py`, `mcp_integration/tools.py`: MCP interfaces.
- `methodology/services/galdr_prompts.py`: reviewer-visible proposed position.

## B. Boundaries
Reuse nullable `display_order`; no schema migration or seed content change. Preserve draft editing and released-playbook admin approval. Do not mutate production playbook content. Preserve unrelated local work.

## C. Architecture
SAO: Shared Services Layer, Hybrid MCP Access, Structured PIPs. Existing act-9 PIP create/ALTER and act-13 MCP scenarios apply.

## D. Tests and gap
Current tests reorder Activities via the service only. No test exercises workflow reordering through the hosted API or reads the position back.
Add failing tests for authenticated API position persistence/read-back, finalization moving first/last and shifting siblings, dry-run rollback, invalid positions/types, and HTTP MCP forwarding. Run PIP/Galdr regressions and release-workflow test suite.

## E. Log story
Workflow apply logs workflow/PIP identity and old/new position; assert successful reorder log. Validation errors reject before persistence.

## F. MCP
Extend existing `add_pip_change` with optional `display_order`, carried to shared service. Existing authenticated user context and human PIP finalization gates remain.

## G. Implementation skeleton
1. Validate requested display position and supported ALTER entity.
2. Persist existing field; expose it through both MCP serializers and REST.
3. Reorder locked siblings stably inside existing apply transaction; include position in review prompts.
4. Red, green, regression, commit, PR, inspect review and checks. Deploy only through existing pipelines after merge is permitted.

## H. UI
No frontend screens changed.
