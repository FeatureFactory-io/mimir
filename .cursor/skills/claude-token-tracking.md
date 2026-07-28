# Skill: Claude Token Tracking

**Capability Domain**: TOKEN_CONSUMPTION
**Technology Stack**: Claude API

## Overview

Track AI token consumption for EST workflow calibration. Logs token usage at the scenario level to `logs/consumption.log` in JSON format, enabling sprint-by-sprint estimate refinement via velocity factor calculation and K-token baseline updates.

## Reference Implementation

### Pattern 1: TokenTracker Utility Class

Create `{app_name}/utils/token_tracker.py`:

```python
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Dedicated logger for token consumption (writes to logs/consumption.log)
consumption_logger = logging.getLogger('consumption')

@dataclass
class TokenConsumption:
    """Token consumption record for EST workflow."""
    timestamp: str
    scenario_id: str
    user_id: int
    sprint: int
    tokens_used: int
    model: str
    operation: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for logging."""
        data = asdict(self)
        return json.dumps(data, separators=(',', ':'))


class TokenTracker:
    """
    Track AI token consumption for EST workflow calibration.
    
    Usage:
        tracker = TokenTracker(
            scenario_id="FOB-PLAYBOOKS-LIST-01",
            user_id=request.user.id,
            sprint=1
        )
        tracker.start()
        # ... AI-assisted work happens ...
        tracker.end(tokens_used=15234, model="claude-3-5-sonnet-20241022")
    
    The tracker logs to consumption.log in JSON format compatible with
    EST-08 Sprint Close & Rebaseline activity.
    """
    
    def __init__(
        self,
        scenario_id: str,
        user_id: int,
        sprint: int = 1,
        operation: str = "implement"
    ):
        """
        Initialize token tracker.
        
        :param scenario_id: BDD scenario ID (e.g., "FOB-PLAYBOOKS-LIST-01")
        :param user_id: User ID performing the work
        :param sprint: Sprint number (default: 1)
        :param operation: Operation type (default: "implement")
        """
        self.scenario_id = scenario_id
        self.user_id = user_id
        self.sprint = sprint
        self.operation = operation
        self.start_time = None
        self.metadata = {}
    
    def start(self, **metadata):
        """
        Start tracking token consumption.
        
        :param metadata: Additional metadata to log (e.g., feature_name, activity)
        """
        self.start_time = datetime.utcnow()
        self.metadata.update(metadata)
        
        consumption_logger.debug(
            f"Token tracking started | "
            f"scenario_id={self.scenario_id} | "
            f"user_id={self.user_id} | "
            f"sprint={self.sprint}"
        )
    
    def end(
        self,
        tokens_used: int,
        model: str,
        status: str = "completed",
        **additional_metadata
    ):
        """
        End tracking and log token consumption.
        
        :param tokens_used: Total tokens consumed
        :param model: AI model used (e.g., "claude-3-5-sonnet-20241022")
        :param status: Status (default: "completed", or "partial", "failed")
        :param additional_metadata: Additional metadata to include
        """
        if self.start_time is None:
            consumption_logger.warning(
                f"Token tracking ended without start | "
                f"scenario_id={self.scenario_id}"
            )
            self.start_time = datetime.utcnow()
        
        # Merge metadata
        self.metadata.update(additional_metadata)
        
        # Create consumption record
        record = TokenConsumption(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            scenario_id=self.scenario_id,
            user_id=self.user_id,
            sprint=self.sprint,
            tokens_used=tokens_used,
            model=model,
            operation=self.operation,
            status=status,
            metadata=self.metadata if self.metadata else None
        )
        
        # Log as JSON (one line per record)
        consumption_logger.info(record.to_json())
        
        # Also log human-readable summary to app.log
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        logging.info(
            f"[TokenTracker] Token consumption logged | "
            f"scenario_id={self.scenario_id} | "
            f"tokens={tokens_used} | "
            f"model={model} | "
            f"duration_sec={duration:.1f}"
        )
    
    def log_immediate(
        self,
        tokens_used: int,
        model: str,
        status: str = "completed",
        **metadata
    ):
        """
        Log token consumption immediately without start/end tracking.
        
        :param tokens_used: Total tokens consumed
        :param model: AI model used
        :param status: Status (default: "completed")
        :param metadata: Additional metadata
        """
        self.metadata.update(metadata)
        
        record = TokenConsumption(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            scenario_id=self.scenario_id,
            user_id=self.user_id,
            sprint=self.sprint,
            tokens_used=tokens_used,
            model=model,
            operation=self.operation,
            status=status,
            metadata=self.metadata if self.metadata else None
        )
        
        consumption_logger.info(record.to_json())


def log_token_consumption(
    scenario_id: str,
    user_id: int,
    tokens_used: int,
    model: str,
    sprint: int = 1,
    operation: str = "implement",
    status: str = "completed",
    **metadata
):
    """
    Convenience function to log token consumption in one call.
    
    :param scenario_id: BDD scenario ID
    :param user_id: User ID
    :param tokens_used: Tokens consumed
    :param model: AI model used
    :param sprint: Sprint number
    :param operation: Operation type
    :param status: Status
    :param metadata: Additional metadata
    """
    tracker = TokenTracker(scenario_id, user_id, sprint, operation)
    tracker.log_immediate(tokens_used, model, status, **metadata)
```

### Pattern 2: Integration with BPE Workflow

Track tokens during feature implementation:

```python
# In BPE-02 (Implement Backend) or similar
from {app_name}.utils.token_tracker import TokenTracker

def implement_scenario(scenario_id, user_id, sprint=1):
    """Implement a BDD scenario with token tracking."""
    tracker = TokenTracker(
        scenario_id=scenario_id,
        user_id=user_id,
        sprint=sprint,
        operation="implement"
    )
    
    tracker.start(
        feature_name="Playbook Management",
        activity="BPE-02-Implement_Backend"
    )
    
    try:
        # AI-assisted implementation happens here
        # (This would be done via Cascade/Windsurf in practice)
        
        # Example: Track tokens from Claude API response
        tokens_used = get_tokens_from_claude_response()  # See Pattern 3
        
        tracker.end(
            tokens_used=tokens_used,
            model="claude-3-5-sonnet-20241022",
            status="completed",
            files_modified=["models.py", "services.py", "views.py"],
            tests_written=5
        )
        
    except Exception as e:
        # Log partial completion if failed
        tracker.end(
            tokens_used=get_tokens_from_claude_response(),
            model="claude-3-5-sonnet-20241022",
            status="failed",
            error=str(e)
        )
        raise
```

### Pattern 3: Extract Tokens from Claude API

Methods to extract token usage from Claude API responses:

```python
import anthropic
import os

def get_claude_client():
    """Get Claude API client."""
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def call_claude_with_tracking(
    prompt: str,
    scenario_id: str,
    user_id: int,
    sprint: int = 1,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096
) -> tuple[str, int]:
    """
    Call Claude API and return response with token count.
    
    :param prompt: Prompt to send to Claude
    :param scenario_id: Scenario ID for tracking
    :param user_id: User ID
    :param sprint: Sprint number
    :param model: Claude model to use
    :param max_tokens: Max tokens in response
    :return: Tuple of (response_text, tokens_used)
    """
    client = get_claude_client()
    
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Extract token usage from response
    tokens_used = response.usage.input_tokens + response.usage.output_tokens
    
    # Log token consumption
    log_token_consumption(
        scenario_id=scenario_id,
        user_id=user_id,
        tokens_used=tokens_used,
        model=model,
        sprint=sprint,
        operation="ai_call",
        status="completed",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )
    
    return response.content[0].text, tokens_used


def aggregate_tokens_from_api_logs(api_key: str, start_date: str, end_date: str) -> dict:
    """
    Aggregate token usage from Claude API usage logs.
    
    :param api_key: Claude API key
    :param start_date: Start date (ISO format)
    :param end_date: End date (ISO format)
    :return: Dict with aggregated token usage
    
    Note: This requires access to Anthropic's usage API.
    Check https://docs.anthropic.com/claude/reference/usage
    """
    # This is a placeholder - actual implementation depends on
    # Anthropic's usage API availability
    client = anthropic.Anthropic(api_key=api_key)
    
    # Hypothetical usage API call
    # usage = client.usage.list(start_date=start_date, end_date=end_date)
    
    # For now, parse from consumption.log
    return parse_consumption_log(start_date, end_date)
```

### Pattern 4: Parse consumption.log for EST Workflow

Utilities for EST-08 Sprint Close & Rebaseline:

```python
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

def parse_consumption_log(
    log_file: Path = Path('logs/consumption.log'),
    sprint: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict]:
    """
    Parse consumption.log and return records.
    
    :param log_file: Path to consumption.log
    :param sprint: Filter by sprint number
    :param start_date: Filter by start date (ISO format)
    :param end_date: Filter by end date (ISO format)
    :return: List of consumption records
    """
    records = []
    
    if not log_file.exists():
        return records
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                # Parse JSON log entry
                record = json.loads(line.strip())
                
                # Apply filters
                if sprint is not None and record.get('sprint') != sprint:
                    continue
                
                if start_date and record.get('timestamp', '') < start_date:
                    continue
                
                if end_date and record.get('timestamp', '') > end_date:
                    continue
                
                records.append(record)
                
            except json.JSONDecodeError:
                continue
    
    return records


def aggregate_tokens_by_scenario(records: List[Dict]) -> Dict[str, int]:
    """
    Aggregate token usage by scenario ID.
    
    :param records: List of consumption records
    :return: Dict mapping scenario_id to total tokens
    """
    totals = defaultdict(int)
    
    for record in records:
        scenario_id = record.get('scenario_id')
        tokens = record.get('tokens_used', 0)
        totals[scenario_id] += tokens
    
    return dict(totals)


def compute_velocity_factor(
    scenario_id: str,
    estimated_tokens: int,
    records: List[Dict]
) -> float:
    """
    Compute velocity factor for a scenario.
    
    Velocity Factor = Actual Tokens / Estimated Tokens
    
    :param scenario_id: Scenario ID
    :param estimated_tokens: Estimated tokens from EST-05
    :param records: Consumption records
    :return: Velocity factor
    """
    actual_tokens = sum(
        r.get('tokens_used', 0)
        for r in records
        if r.get('scenario_id') == scenario_id
    )
    
    if estimated_tokens == 0:
        return 1.0
    
    return actual_tokens / estimated_tokens


def generate_sprint_report(sprint: int, log_file: Path = Path('logs/consumption.log')) -> str:
    """
    Generate sprint token consumption report for EST-08.
    
    :param sprint: Sprint number
    :param log_file: Path to consumption.log
    :return: Markdown report
    """
    records = parse_consumption_log(log_file, sprint=sprint)
    totals = aggregate_tokens_by_scenario(records)
    
    report = f"# Sprint {sprint} Token Consumption Report\n\n"
    report += f"**Total Scenarios**: {len(totals)}\n"
    report += f"**Total Tokens**: {sum(totals.values()):,}\n\n"
    report += "## By Scenario\n\n"
    report += "| Scenario ID | Tokens Used | Status |\n"
    report += "|-------------|-------------|--------|\n"
    
    for scenario_id, tokens in sorted(totals.items()):
        # Get status from last record for this scenario
        scenario_records = [r for r in records if r.get('scenario_id') == scenario_id]
        status = scenario_records[-1].get('status', 'unknown') if scenario_records else 'unknown'
        report += f"| {scenario_id} | {tokens:,} | {status} |\n"
    
    return report
```

### Pattern 5: Django Management Command

Create management command for sprint reports:

**File**: `{app_name}/management/commands/sprint_token_report.py`

```python
from django.core.management.base import BaseCommand
from pathlib import Path
from {app_name}.utils.token_tracker import generate_sprint_report

class Command(BaseCommand):
    help = 'Generate sprint token consumption report'
    
    def add_arguments(self, parser):
        parser.add_argument('sprint', type=int, help='Sprint number')
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (default: stdout)'
        )
    
    def handle(self, *args, **options):
        sprint = options['sprint']
        output_file = options.get('output')
        
        self.stdout.write(f'Generating report for Sprint {sprint}...')
        
        report = generate_sprint_report(sprint)
        
        if output_file:
            Path(output_file).write_text(report)
            self.stdout.write(
                self.style.SUCCESS(f'Report written to {output_file}')
            )
        else:
            self.stdout.write(report)
```

Usage:
```bash
python manage.py sprint_token_report 1
python manage.py sprint_token_report 1 --output docs/plans/SPRINT_1_TOKENS.md
```

### Pattern 6: Windsurf/Cascade Integration

Track tokens when using Windsurf/Cascade for development:

```python
# Add to project's AI context or workflow scripts
def track_cascade_session(scenario_id: str, user_id: int, sprint: int):
    """
    Track a Cascade development session.
    
    Note: This requires manual token extraction from Cascade logs
    or API usage dashboard.
    """
    from {app_name}.utils.token_tracker import TokenTracker
    
    tracker = TokenTracker(
        scenario_id=scenario_id,
        user_id=user_id,
        sprint=sprint,
        operation="cascade_session"
    )
    
    tracker.start(
        tool="Windsurf/Cascade",
        session_type="feature_implementation"
    )
    
    # Development happens...
    # After session, manually log tokens from Cascade usage dashboard
    
    # Example: User checks Claude dashboard and sees 45,230 tokens used
    tracker.end(
        tokens_used=45230,
        model="claude-3-5-sonnet-20241022",
        status="completed",
        files_modified=12,
        tests_written=8,
        commits=3
    )
```

## consumption.log Format

Each line is a JSON object:

```json
{"timestamp": "2026-04-08T14:30:00.123Z", "scenario_id": "FOB-PLAYBOOKS-LIST-01", "user_id": 1, "sprint": 1, "tokens_used": 15234, "model": "claude-3-5-sonnet-20241022", "operation": "implement", "status": "completed", "metadata": {"feature_name": "Playbook Management", "activity": "BPE-02", "files_modified": ["models.py", "services.py"], "tests_written": 5}}
```

**Fields**:
- `timestamp`: ISO 8601 UTC timestamp
- `scenario_id`: BDD scenario ID (e.g., "FOB-PLAYBOOKS-LIST-01")
- `user_id`: User ID performing work
- `sprint`: Sprint number
- `tokens_used`: Total tokens consumed
- `model`: AI model identifier
- `operation`: Operation type ("implement", "test", "refactor", "debug", etc.)
- `status`: "completed", "partial", "failed"
- `metadata`: Optional dict with additional context

## EST-08 Integration

### Sprint Close Workflow

1. **Collect actuals** from `consumption.log`:
   ```python
   records = parse_consumption_log(sprint=1)
   totals = aggregate_tokens_by_scenario(records)
   ```

2. **Compute velocity factors**:
   ```python
   for scenario_id, actual_tokens in totals.items():
       estimated = get_estimate_from_excel(scenario_id)
       vf = compute_velocity_factor(scenario_id, estimated, records)
       print(f"{scenario_id}: VF={vf:.2f}")
   ```

3. **Update K-token baselines** in Reference Table

4. **Re-run Monte Carlo** simulation with calibrated data

## Testing Token Tracking

```python
# tests/test_token_tracker.py
import json
from pathlib import Path
from {app_name}.utils.token_tracker import TokenTracker, parse_consumption_log

def test_token_tracker_logs_json(tmp_path):
    """Verify TokenTracker logs valid JSON."""
    log_file = tmp_path / 'consumption.log'
    
    # Configure logger to use temp file
    # ... logger configuration ...
    
    tracker = TokenTracker(
        scenario_id="TEST-01",
        user_id=1,
        sprint=1
    )
    tracker.log_immediate(
        tokens_used=1000,
        model="claude-3-5-sonnet-20241022"
    )
    
    # Verify log file
    assert log_file.exists()
    
    # Verify JSON format
    with open(log_file) as f:
        record = json.loads(f.readline())
        assert record['scenario_id'] == "TEST-01"
        assert record['tokens_used'] == 1000

def test_parse_consumption_log():
    """Verify consumption log parsing."""
    records = parse_consumption_log(sprint=1)
    assert isinstance(records, list)
    
    if records:
        assert 'scenario_id' in records[0]
        assert 'tokens_used' in records[0]
```

## References

- Activity **EST-08** (Sprint Close and Rebaseline) - Sprint close workflow
- Activity **EST-05** (Produce Rough Estimates) - Token estimation
- Anthropic Claude API: https://docs.anthropic.com/claude/reference/
- Anthropic Usage API: https://docs.anthropic.com/claude/reference/usage

