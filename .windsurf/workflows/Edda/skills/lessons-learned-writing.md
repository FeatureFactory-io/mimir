# Skill: Lessons Learned Writing

**Capability Domain**: LESSONS_LEARNED  
**Technology Stack**: Markdown + GitHub CLI

## Overview

Patterns for computing iteration metrics from GitHub data, writing the `docs/lessons_learned/ITER-*.md` retrospective file, and identifying PIP candidates. The `<!-- LEARNING -->` YAML block is the machine-readable portion that PIT-01 parses for orient briefing.

## Reference Implementation

### Pattern 1: Compute Metrics from GitHub Data

```python
import subprocess, json, re
from datetime import datetime

def compute_iteration_metrics(milestone_number: int) -> dict:
    """
    Compute iteration metrics from closed GitHub milestone issues and comments.

    :param milestone_number: GitHub milestone number. Example: 15
    :return: Metrics dict. Example: {velocity_ratio: 0.75, dominant_drift_cause: 'checkpoint_fail', ...}
    """
    # Get all issues for milestone
    issues = json.loads(subprocess.check_output([
        'gh', 'issue', 'list', '--milestone', str(milestone_number),
        '--state', 'all', '--json', 'number,title,labels,closedAt,body,comments'
    ]))

    scenarios_planned = len(issues)
    scenarios_completed = 0
    scenarios_abandoned = 0
    drift_causes = []
    footprint_violations = []   # files outside declared footprint
    method_explosion_events = []
    sao_violation_events = []
    rework_events = 0

    for issue in issues:
        labels = [l['name'] for l in issue['labels']]
        if 'status-done' in labels:
            scenarios_completed += 1
        elif issue.get('closedAt'):  # closed but not status-done = dropped
            scenarios_abandoned += 1

        # Parse comments for drift signal data
        for comment in issue.get('comments', []):
            body = comment.get('body', '')

            # Extract drift signal type from absorbed/escalated comments
            drift_match = re.search(r'type: (\S+)', body)
            if ('<!-- DRIFT absorbed -->' in body or '<!-- ESCALATE -->' in body) and drift_match:
                signal = drift_match.group(1)
                drift_causes.append(signal)

                if signal == 'footprint_violation':
                    file_match = re.search(r'evidence: (.+)', body)
                    if file_match:
                        footprint_violations.append(file_match.group(1).strip())

                elif signal == 'method_explosion':
                    method_match = re.search(r'evidence: (.+)', body)
                    if method_match:
                        method_explosion_events.append(method_match.group(1).strip())

                elif signal == 'sao_violation':
                    sao_match = re.search(r'evidence: (.+)', body)
                    if sao_match:
                        sao_violation_events.append(sao_match.group(1).strip())

            # Count rework events (checkpoint_fail absorbed + retried)
            if 'checkpoint_fail_retry' in body:
                rework_events += 1

    velocity_ratio = scenarios_completed / scenarios_planned if scenarios_planned > 0 else 0
    dominant_drift_cause = max(set(drift_causes), key=drift_causes.count) if drift_causes else 'none'
    footprint_accuracy = (scenarios_completed - len(footprint_violations)) / scenarios_completed if scenarios_completed > 0 else 1.0

    return {
        'scenarios_planned': scenarios_planned,
        'scenarios_completed': scenarios_completed,
        'scenarios_abandoned': scenarios_abandoned,
        'velocity_ratio': round(velocity_ratio, 2),
        'dominant_drift_cause': dominant_drift_cause,
        'footprint_violations': footprint_violations,
        'footprint_accuracy': round(max(footprint_accuracy, 0.0), 2),
        'method_explosion_events': method_explosion_events,
        'sao_violation_events': sao_violation_events,
        'rework_events': rework_events,
    }
```

### Pattern 2: Write Lessons Learned File

```python
def write_lessons_learned(milestone_number: int, goal: str, metrics: dict, narrative: str, drift_events: list, pip_candidates: list) -> str:
    """
    Write the lessons learned markdown file for an iteration.

    :param milestone_number: GitHub milestone number. Example: 15
    :param goal: Iteration goal sentence. Example: "Ship workflow export+import via MCP"
    :param metrics: Computed metrics dict from compute_iteration_metrics(). Example: {velocity_ratio: 0.75, ...}
    :param narrative: Human-readable description of what happened. Example: "S1 completed cleanly, S2 had a footprint violation..."
    :param drift_events: List of drift event dicts. Example: [{type: 'checkpoint_fail', scenario: 'S1', resolved: True}]
    :param pip_candidates: List of PIP proposals. Example: ["Add MCP smoke check to PIT-02"]
    :return: Path to written file. Example: "docs/lessons_learned/ITER-20260413-1800-workflow-export.md"
    """
    from pathlib import Path
    from datetime import datetime

    slug = goal.lower().replace(' ', '-')[:40].rstrip('-')
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M')
    filename = f"ITER-{timestamp}-{slug}.md"
    filepath = Path('docs/lessons_learned') / filename
    filepath.parent.mkdir(exist_ok=True)

    content = f"""<!-- LEARNING -->
milestone: {milestone_number}
goal: "{goal}"
velocity_ratio: {metrics['velocity_ratio']}
scenarios_planned: {metrics['scenarios_planned']}
scenarios_completed: {metrics['scenarios_completed']}
scenarios_abandoned: {metrics['scenarios_abandoned']}
dominant_drift_cause: {metrics['dominant_drift_cause']}
footprint_accuracy: {metrics['footprint_accuracy']}
footprint_violations:
{chr(10).join(f'  - {f}' for f in metrics['footprint_violations']) or '  []'}
method_explosion_events: {len(metrics['method_explosion_events'])}
sao_violation_events: {len(metrics['sao_violation_events'])}
rework_events: {metrics['rework_events']}
<!-- /LEARNING -->

## What Happened
{narrative}

## Drift Events
{chr(10).join(f'- **{e["type"]}** on {e["scenario"]}: {e.get("resolution", "see issue")}' for e in drift_events) or 'No drift events.'}

## Footprint Accuracy
Accuracy: {metrics['footprint_accuracy']:.0%}  
{f'Footprint violations in: {metrics["footprint_violations"]}' if metrics['footprint_violations'] else 'All files within declared footprint.'}

## SAO & Method Health
- Method explosion events: {len(metrics['method_explosion_events'])}
- SAO violation events: {len(metrics['sao_violation_events'])}

## What to Change
{chr(10).join(f'- [ ] PIP: {p}' for p in pip_candidates) or '- [ ] No PIP candidates identified.'}

## Raw Metrics
| Metric | Value |
|---|---|
| Velocity ratio | {metrics['velocity_ratio']:.0%} |
| Rework events | {metrics['rework_events']} |
| Footprint accuracy | {metrics['footprint_accuracy']:.0%} |
| Method explosion events | {len(metrics['method_explosion_events'])} |
| SAO violation events | {len(metrics['sao_violation_events'])} |
"""

    filepath.write_text(content)
    return str(filepath)
```

### Pattern 3: Identify PIP Candidates

Common PIP trigger patterns from lessons learned data:

| Pattern | PIP Candidate |
|---|---|
| `dominant_drift_cause == checkpoint_fail` for 2+ iterations | Add pre-scenario test smoke check to PIT-02 Contract |
| `footprint_accuracy < 0.7` for 2+ iterations | Improve footprint estimation in PIT-02 (use AST analysis on skeleton) |
| Same file in `footprint_violations` 2+ times | Split that file by domain in architecture |
| `velocity_ratio < 0.7` for 2+ iterations | Reduce default scenario scope in PIT-02 Contract |
| `rework_events > 1` per iteration | Add test-compile check before checkpoint in MIT-02 |
| `method_explosion_events > 0` for 2+ iterations | Add method-size guard to code review checklist |
| `sao_violation_events > 0` for 2+ iterations | Improve SAO section tagging in BPE-01 Plan Feature |

## File Naming Convention

```
docs/lessons_learned/ITER-YYYYMMDD-HHmm-goal-slug.md

Examples:
ITER-20260413-1800-ship-workflow-export-import.md
ITER-20260414-0900-add-agent-crud-web-ui.md
```

## Quality Gates

- [ ] `<!-- LEARNING -->` block is valid YAML (parseable by PyYAML)
- [ ] `velocity_ratio`, `dominant_drift_cause`, `footprint_accuracy` all computed
- [ ] `footprint_violations` list is accurate (from footprint_violation drift events)
- [ ] `method_explosion_events` and `sao_violation_events` counts are present
- [ ] `## What to Change` section has at least one PIP candidate or explicit "No PIP candidates"
- [ ] File committed to `docs/lessons_learned/` before closing milestone
