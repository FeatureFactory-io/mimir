# Skill: Django Logging Setup

**Capability Domain**: BACKEND_LOGGING
**Technology Stack**: Django+Python

## Overview

Configure Django's LOGGING settings to implement informative, structured logging with file rotation. Enables effective troubleshooting by logging who, what, why, where, and when for every significant operation. Supports three log files: `app.log` (backend operations), `gui.log` (frontend events), and `consumption.log` (token tracking).

## Reference Implementation

### Pattern 1: Django LOGGING Configuration

Add to `{project_name}/settings.py`:

```python
import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{name}:{funcName}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'format': '{message}',
            'style': '{',
        },
    },
    'handlers': {
        'app_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'gui_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'gui.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'consumption_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'consumption.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'json',  # JSON format for EST workflow parsing
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['app_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        '{project_name}': {
            'handlers': ['app_file', 'console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'gui': {
            'handlers': ['gui_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'consumption': {
            'handlers': ['consumption_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['app_file', 'console'],
        'level': 'INFO',
    },
}
```

### Pattern 2: Create Logs Directory

Add to project initialization (e.g., `manage.py` or `wsgi.py`):

```python
import os
from pathlib import Path

# Ensure logs directory exists
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
```

Or create via shell script in BSP workflow:

```bash
mkdir -p logs
touch logs/.gitkeep

# Add to .gitignore
cat >> .gitignore << 'EOF'

# Logs
logs/*.log
!logs/.gitkeep
EOF
```

### Pattern 3: Informative Logging in Services

Follow informative logging pattern - include context for troubleshooting:

```python
import logging

logger = logging.getLogger(__name__)

class PlaybookService:
    """Service layer for playbook operations."""
    
    def create_playbook(self, name, description, category, author):
        """
        Create a new playbook.
        
        :param name: Playbook name
        :param description: Playbook description
        :param category: Category (e.g., 'development', 'testing')
        :param author: User instance
        :return: Created Playbook instance
        :raises ValidationError: If validation fails
        """
        logger.info(
            f"[{__name__}.create_playbook] Starting playbook creation | "
            f"user_id={author.id} | name={name} | category={category}"
        )
        
        try:
            # Validation
            if not name or len(name) < 3:
                raise ValidationError("Playbook name must be at least 3 characters")
            
            # Create playbook
            playbook = Playbook.objects.create(
                name=name,
                description=description,
                category=category,
                author=author,
                status='draft',
                version='0.1'
            )
            
            logger.info(
                f"[{__name__}.create_playbook] Playbook created successfully | "
                f"user_id={author.id} | playbook_id={playbook.id} | "
                f"name={playbook.name} | version={playbook.version}"
            )
            
            return playbook
            
        except ValidationError as e:
            logger.warning(
                f"[{__name__}.create_playbook] Validation failed | "
                f"user_id={author.id} | name={name} | error={str(e)}"
            )
            raise
            
        except Exception as e:
            logger.error(
                f"[{__name__}.create_playbook] Unexpected error | "
                f"user_id={author.id} | name={name} | "
                f"error_type={type(e).__name__} | error={str(e)}",
                exc_info=True
            )
            raise
```

### Pattern 4: Logging in Views

```python
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

logger = logging.getLogger(__name__)

@login_required
def playbook_create(request):
    """Create new playbook."""
    logger.info(
        f"[{__name__}.playbook_create] View accessed | "
        f"user_id={request.user.id} | method={request.method}"
    )
    
    if request.method == 'POST':
        try:
            service = PlaybookService()
            playbook = service.create_playbook(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                category=request.POST.get('category'),
                author=request.user
            )
            
            logger.info(
                f"[{__name__}.playbook_create] Playbook created via view | "
                f"user_id={request.user.id} | playbook_id={playbook.id}"
            )
            
            messages.success(request, f'Playbook "{playbook.name}" created successfully')
            return redirect('playbook_detail', playbook_id=playbook.id)
            
        except ValidationError as e:
            logger.warning(
                f"[{__name__}.playbook_create] Form validation failed | "
                f"user_id={request.user.id} | error={str(e)}"
            )
            messages.error(request, str(e))
    
    return render(request, 'playbooks/create.html', {
        'page_title': 'Create Playbook'
    })
```

### Pattern 5: Logging in Models (Signals)

```python
import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Playbook)
def log_playbook_save(sender, instance, created, **kwargs):
    """Log playbook creation/update."""
    action = 'created' if created else 'updated'
    logger.info(
        f"[signals.log_playbook_save] Playbook {action} | "
        f"playbook_id={instance.id} | name={instance.name} | "
        f"author_id={instance.author.id} | version={instance.version} | "
        f"status={instance.status}"
    )

@receiver(pre_delete, sender=Playbook)
def log_playbook_delete(sender, instance, **kwargs):
    """Log playbook deletion."""
    logger.warning(
        f"[signals.log_playbook_delete] Playbook being deleted | "
        f"playbook_id={instance.id} | name={instance.name} | "
        f"author_id={instance.author.id}"
    )
```

### Pattern 6: Logging Database Queries (Debug)

For development debugging, enable SQL query logging:

```python
# In settings.py (DEBUG mode only)
if DEBUG:
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }
```

### Pattern 7: Request/Response Middleware Logging

Create custom middleware for request/response logging:

```python
# {app_name}/middleware/logging_middleware.py
import logging
import time

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """Log all HTTP requests and responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request
        start_time = time.time()
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        
        logger.info(
            f"[RequestLoggingMiddleware] Request started | "
            f"method={request.method} | path={request.path} | "
            f"user_id={user_id}"
        )
        
        # Process request
        response = self.get_response(request)
        
        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[RequestLoggingMiddleware] Request completed | "
            f"method={request.method} | path={request.path} | "
            f"user_id={user_id} | status={response.status_code} | "
            f"duration_ms={duration_ms:.2f}"
        )
        
        return response
```

Add to `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    '{app_name}.middleware.logging_middleware.RequestLoggingMiddleware',
]
```

## Informative Logging Checklist

Every log message should include:

- ✅ **Location**: `[module.function]` prefix
- ✅ **Action**: What operation is being performed
- ✅ **Context**: Key identifiers (user_id, entity_id, etc.)
- ✅ **Result**: Success/failure indication
- ✅ **Error details**: Exception type and message (if applicable)

**Good Example**:
```python
logger.info(
    f"[playbook_service.create_playbook] Playbook created successfully | "
    f"user_id={user.id} | playbook_id={playbook.id} | name={playbook.name}"
)
```

**Bad Example**:
```python
logger.info("Playbook created")  # Missing context, location, identifiers
```

## Testing Logging

Verify logging is working:

```python
# tests/test_logging.py
import logging
from pathlib import Path
from django.test import TestCase

class LoggingTestCase(TestCase):
    """Test logging configuration."""
    
    def test_app_log_exists(self):
        """Verify app.log is created."""
        log_file = Path('logs/app.log')
        
        # Trigger a log entry
        logger = logging.getLogger('test')
        logger.info("Test log entry")
        
        # Verify file exists
        self.assertTrue(log_file.exists())
    
    def test_log_rotation(self):
        """Verify log rotation is configured."""
        logger = logging.getLogger('test')
        handler = logger.handlers[0]
        
        self.assertEqual(handler.maxBytes, 10 * 1024 * 1024)
        self.assertEqual(handler.backupCount, 5)
```

## Common Patterns

### Pattern: Logging with Timing

```python
import time

start_time = time.time()
# ... operation ...
duration_ms = (time.time() - start_time) * 1000

logger.info(
    f"[{__name__}.operation] Completed | "
    f"duration_ms={duration_ms:.2f}"
)
```

### Pattern: Logging with Exception Context

```python
try:
    # ... operation ...
except SpecificException as e:
    logger.error(
        f"[{__name__}.operation] Operation failed | "
        f"context_id={id} | error={str(e)}",
        exc_info=True  # Include full traceback
    )
    raise
```

### Pattern: Conditional Debug Logging

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(
        f"[{__name__}.operation] Debug info | "
        f"variable_state={expensive_to_compute()}"
    )
```

## Integration with EST Workflow

The `consumption.log` uses JSON format for EST-08 parsing:

```python
import json
import logging

consumption_logger = logging.getLogger('consumption')

def log_token_consumption(scenario_id, user_id, tokens_used, model, sprint=1):
    """Log token consumption for EST workflow."""
    entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'scenario_id': scenario_id,
        'user_id': user_id,
        'sprint': sprint,
        'tokens_used': tokens_used,
        'model': model,
        'operation': 'implement',
        'status': 'completed'
    }
    consumption_logger.info(json.dumps(entry))
```

## References

- informative logging pattern - Informative logging requirements
- Activity **EST-08** (Sprint Close and Rebaseline) - consumption.log format
- Django Logging Documentation: https://docs.djangoproject.com/en/stable/topics/logging/

