# Skill: Behave-Django BDD Runner

**Capability Domain**: BDD_RUNNER
**Technology Stack**: behave+Django+Playwright

## Overview

Patterns for running BDD acceptance and E2E tests using behave-django. AT uses Django test client under `docs/features/`. E2E uses Playwright + LiveServer under `tests/e2e/`. Same Gherkin phrases; separate step libraries and `environment.py` files.

## Reference Implementation

### Pattern 1: behave.ini Configuration

```ini
[behave]
paths = docs/features
format = pretty
logging_level = INFO
tags = ~@wip
stdout_capture = false
stderr_capture = false
log_capture = false
```

Makefile: `make test-at` → `docs/features/`; `make test-e2e` → `tests/e2e/` (overrides path).

### Pattern 2: environment.py Lifecycle (Acceptance Tests)

```python
# docs/features/environment.py
import django
from django.test.utils import setup_test_environment, teardown_test_environment
from django.core.management import call_command

def before_all(context):
    django.setup()
    setup_test_environment()
    call_command('loaddata', 'tests/fixtures/seed.json')

def before_scenario(context, scenario):
    from django.test import TestCase
    context._test = TestCase('__init__')
    context._test._pre_setup()

def after_scenario(context, scenario):
    context._test._post_teardown()

def after_all(context):
    teardown_test_environment()
```

### Pattern 3: environment.py Lifecycle (E2E Tests with Playwright)

```python
# tests/e2e/environment.py
# Playwright browser, LiveServerTestCase, base_url targeting, screenshot-on-step.
```

AT is not LiveServer. LiveServer belongs to E2E only.
