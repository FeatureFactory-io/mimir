# Skill: GitHub Milestone Operations

**Capability Domain**: GITHUB_MILESTONE  
**Technology Stack**: GitHub CLI

## Overview

Patterns for creating, reading, updating, and closing GitHub Milestones as Iteration records. Covers the `<!-- MANIFEST -->` YAML embedding convention used by PIT and MIT.

## Reference Implementation

### Pattern 1: Create Milestone with MANIFEST Block

```bash
# Create iteration milestone with embedded YAML manifest
gh api repos/{owner}/{repo}/milestones \
  --method POST \
  --field title="ITER-$(date +%Y%m%d) | {iteration_goal}" \
  --field due_on="$(date -u -v+1d +%Y-%m-%dT23:59:59Z)" \
  --field description="$(cat <<'ENDDESC'
<!-- MANIFEST -->
iteration:
  goal: "Ship workflow export+import via MCP"
  doctrine_version: "2.0"
  created_at: "2026-04-13T18:00:00Z"

conflict_map:
  mcp_integration/tools.py: [S1, S2]

parallel_groups:
  A: [S1]
  B: [S3]
  C: [S2]

scenarios:
  S1:
    title: "User can export workflow as JSON"
    github_issue: null
    parallel_group: A
    skeleton_commit: null             # filled by PIT-02 after skeleton commit
    sao_sections:
      - "3.2 Service Layer"
      - "4.1 MCP Tool Contracts"
    context_map:
      - "methodology/services/workflow_service.py:45-89"
      - "mcp_integration/tools.py:120-145"
    do_not_do:
      - "Do not touch auth views — outside footprint"
      - "Do not add fields to Workflow model"
    codebase_footprint:
      - mcp_integration/tools.py
      - methodology/services/workflow_export_service.py
      - tests/integration/test_mcp_export.py
    checkpoint:
      command: "pytest tests/integration/test_mcp_export.py -x"
      expected_exit_code: 0
    dependencies: []
    rollback_point: "git stash"
<!-- /MANIFEST -->

## Iteration Goal
Ship workflow export+import via MCP so that AI-to-AI handoff works.

## Scenarios
- [S1] User can export workflow as JSON
- [S2] User can import workflow from JSON
ENDDESC
)"
```

### Pattern 2: Read and Parse MANIFEST from Milestone

```bash
# Get milestone description
MILESTONE_DESC=$(gh api repos/{owner}/{repo}/milestones/{N} --jq '.description')

# Extract MANIFEST block
MANIFEST_YAML=$(echo "$MILESTONE_DESC" | \
  awk '/<!-- MANIFEST -->/{found=1; next} /<!-- \/MANIFEST -->/{found=0} found{print}')

# Parse with Python (reliable YAML parsing)
python3 - <<EOF
import yaml, sys
manifest = yaml.safe_load("""$MANIFEST_YAML""")
print('Goal:', manifest['iteration']['goal'])
print('Doctrine version:', manifest['iteration']['doctrine_version'])
for sid, scenario in manifest['scenarios'].items():
    print(f'  {sid}: {scenario["title"]} [{scenario["parallel_group"]}]')
    print(f'    skeleton_commit: {scenario.get("skeleton_commit")}')
    print(f'    sao_sections: {scenario.get("sao_sections")}')
EOF
```

### Pattern 3: Update MANIFEST in Milestone Description

```bash
# Read current description
CURRENT_DESC=$(gh api repos/{owner}/{repo}/milestones/{N} --jq '.description')

# Replace MANIFEST block with updated YAML
UPDATED_DESC=$(python3 - <<EOF
import re, yaml

desc = """$CURRENT_DESC"""
new_manifest = """iteration:
  goal: "{new_goal}"
  ..."""

updated = re.sub(
    r'<!-- MANIFEST -->.*?<!-- /MANIFEST -->',
    f'<!-- MANIFEST -->\n{new_manifest}\n<!-- /MANIFEST -->',
    desc,
    flags=re.DOTALL
)
print(updated)
EOF
)

# Patch milestone
gh api repos/{owner}/{repo}/milestones/{N} \
  --method PATCH \
  --field description="$UPDATED_DESC"
```

### Pattern 4: Close Milestone

```bash
# Verify all issues are closed first
OPEN_COUNT=$(gh issue list --milestone {N} --state open --json number | jq 'length')
if [ "$OPEN_COUNT" -gt 0 ]; then
  echo "ERROR: $OPEN_COUNT issues still open. Cannot close milestone."
  exit 1
fi

# Close the milestone
gh api repos/{owner}/{repo}/milestones/{N} \
  --method PATCH \
  --field state="closed"

echo "Milestone {N} closed."
```

### Pattern 5: Get Milestone Progress

```bash
# Get milestone stats
gh api repos/{owner}/{repo}/milestones/{N} \
  --jq '{title: .title, open: .open_issues, closed: .closed_issues, pct: (.closed_issues / (.open_issues + .closed_issues) * 100 | floor)}'
```

## MANIFEST YAML Schema

```yaml
iteration:
  goal: string                    # "Verb noun so that success signal"
  doctrine_version: string        # "2.0"
  created_at: ISO8601             # "2026-04-13T18:00:00Z"

conflict_map:
  {filename}: [S1, S2]            # files shared between scenarios; derived from
                                  # git diff of skeleton commits, not speculative

parallel_groups:
  A: [S1]                         # first group to execute
  B: [S3]                         # can run parallel with A
  C: [S2]                         # depends on A

scenarios:
  S{N}:
    title: string
    github_issue: int              # null until PIT-03 runs
    parallel_group: string         # A/B/C
    skeleton_commit: string        # commit hash after PIT-02 skeleton; null until then
    sao_sections: [string]         # SAO.md section headings that constrain this scenario
    context_map: [string]          # 3-5 "file:line_range" references for cold-start
    do_not_do: [string]            # explicit out-of-scope guardrails
    codebase_footprint: [string]   # exact file paths from skeleton diff
    checkpoint:
      command: string              # pytest command
      expected_exit_code: int      # 0
    dependencies: [string]         # ["S1"] or []
    rollback_point: string         # "git stash"
```

## Quality Gates

- [ ] Milestone title follows `ITER-YYYYMMDD | {goal}` pattern
- [ ] `<!-- MANIFEST -->` block present and parseable as YAML
- [ ] `doctrine_version` is `"2.0"`
- [ ] All required scenario fields present: `title`, `github_issue`, `parallel_group`, `skeleton_commit`, `sao_sections`, `context_map`, `do_not_do`, `codebase_footprint`, `checkpoint`, `dependencies`, `rollback_point`
- [ ] No `time_budget_minutes` or `target_duration_minutes` fields present
- [ ] `conflict_map` entries derived from actual skeleton commit diffs (not speculative)
