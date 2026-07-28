# Skill: Pytest Log Story Assertions

**Capability Domain**: LOG_STORY_TESTING
**Technology Stack**: pytest+caplog+Python

## Overview

Prove Log Story Script rows with pytest `caplog` using a shared helper. Turns observability from “statements exist” into a failing test when the narrative regresses.

## Reference Implementation

### Pattern 1: Helper — `tests/support/log_story.py`

```python
from __future__ import annotations

import logging
from typing import Mapping, Sequence


def assert_log_story(
    caplog,
    *,
    where: str,
    beats: Mapping[str, Sequence[str]],
    level: str = "INFO",
) -> None:
    """Assert each beat has a matching log record for ``where``.

    :param caplog: pytest ``caplog`` fixture
    :param where: Class.method (or stable substring) that must appear
    :param beats: beat name → list of required substrings (all must appear in one record)
    :param level: minimum level name (INFO default)
    :raises AssertionError: naming the missing beat / substring
    """
    min_level = getattr(logging, level.upper(), logging.INFO)
    records = [
        r
        for r in caplog.records
        if r.levelno >= min_level and where in r.getMessage()
    ]
    messages = [r.getMessage() for r in records]
    for beat, needles in beats.items():
        matched = [
            msg
            for msg in messages
            if all(n in msg for n in needles)
        ]
        if not matched:
            raise AssertionError(
                f"log story missing beat={beat!r} where={where!r} "
                f"needles={list(needles)!r}; saw={messages!r}"
            )
```

### Pattern 2: View / integration test

```python
import logging
import pytest
from django.urls import reverse
from tests.support.log_story import assert_log_story

@pytest.mark.django_db
def test_login_log_story_reject(client, django_user_model, caplog):
    django_user_model.objects.create_user(
        username="elena", email="elena@example.com", password="secret"
    )
    with caplog.at_level(logging.INFO, logger="yggdrasil.auth"):
        client.post(
            reverse("auth:login"),
            {"email": "elena@example.com", "password": "wrong"},
        )
    assert_log_story(
        caplog,
        where="LoginView.post",
        beats={
            "entry": ["attempt", "email="],
            "branch": ["authentication failed"],
        },
    )
```

### Pattern 3: Manifest wiring

```yaml
log_tests:
  - {name: test_login_log_story_reject, path: path/to/test_file.py}
checkpoint:
  log_story_command: "pytest path/to/test_file.py::test_login_log_story_reject -x"
```

## Common Pitfalls

- Asserting only status codes and skipping caplog
- Matching on password / token values
- Using a separate “logging slice” after behavior is green
- Over-strict exact full-string match (prefer stable `must_include` fragments)

## Quality Gates

- [ ] `tests/support/log_story.py` importable
- [ ] Happy and reject log-story tests where both paths exist
- [ ] Failure message names missing beat
- [ ] Linked from BPE-02 / MIN-04 / TFK-02
