# Skill: HTMX Frontend Logging

**Capability Domain**: FRONTEND_LOGGING
**Technology Stack**: HTMX+JavaScript

## Overview

Implement frontend logging for HTMX interactions, JavaScript errors, and user actions. Logs are captured in the browser console and sent to a Django backend endpoint for persistence in `logs/gui.log`. Enables troubleshooting of frontend issues and tracking user interaction patterns.

## Reference Implementation

### Pattern 1: JavaScript Logger Class

Create `static/js/logger.js`:

```javascript
/**
 * Frontend Logger - logs to console and sends to backend for gui.log
 * 
 * Usage:
 *   Logger.info('Button clicked', { button_id: 'save-btn', entity_id: 123 });
 *   Logger.error('Form validation failed', { form: 'playbook-create', errors: [...] });
 */
const Logger = {
    /**
     * Internal log method - sends to console and backend
     */
    _log(level, message, context = {}) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            level: level.toUpperCase(),
            timestamp: timestamp,
            message: message,
            context: context,
            url: window.location.pathname,
            user_agent: navigator.userAgent,
        };
        
        // Console output (always)
        const consoleMethod = console[level] || console.log;
        consoleMethod(
            `[${level.toUpperCase()}] ${timestamp} ${message}`,
            context
        );
        
        // Send to backend for gui.log (async, non-blocking)
        this._sendToBackend(logEntry);
    },
    
    /**
     * Send log entry to Django backend
     */
    _sendToBackend(logEntry) {
        fetch('/api/log/gui/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this._getCsrfToken(),
            },
            body: JSON.stringify(logEntry),
        }).catch(err => {
            // Don't log to backend again (avoid infinite loop)
            console.error('Failed to send log to backend:', err);
        });
    },
    
    /**
     * Get CSRF token from DOM
     */
    _getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            // Try cookie fallback
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
            return cookieValue || '';
        }
        return token;
    },
    
    /**
     * Public logging methods
     */
    debug(message, context) {
        this._log('debug', message, context);
    },
    
    info(message, context) {
        this._log('info', message, context);
    },
    
    warn(message, context) {
        this._log('warn', message, context);
    },
    
    error(message, context) {
        this._log('error', message, context);
    },
};

// Make Logger globally available
window.Logger = Logger;
```

### Pattern 2: HTMX Event Logging

Add HTMX event listeners to `static/js/logger.js` or separate file:

```javascript
/**
 * HTMX Event Logging
 * Automatically logs all HTMX requests and responses
 */

// Log when HTMX request starts
document.body.addEventListener('htmx:beforeRequest', (event) => {
    const target = event.detail.target;
    const targetId = target.id || target.getAttribute('data-testid') || target.tagName;
    
    Logger.info('HTMX request started', {
        event: 'htmx:beforeRequest',
        target: targetId,
        method: event.detail.verb,
        url: event.detail.path,
        trigger: event.detail.triggeringEvent?.type,
    });
});

// Log when HTMX request completes
document.body.addEventListener('htmx:afterRequest', (event) => {
    const target = event.detail.target;
    const targetId = target.id || target.getAttribute('data-testid') || target.tagName;
    const successful = event.detail.successful;
    const level = successful ? 'info' : 'error';
    
    Logger[level]('HTMX request completed', {
        event: 'htmx:afterRequest',
        target: targetId,
        method: event.detail.verb,
        url: event.detail.path,
        status: event.detail.xhr.status,
        successful: successful,
        elapsed_ms: event.detail.elapsed,
    });
});

// Log HTMX response errors
document.body.addEventListener('htmx:responseError', (event) => {
    const target = event.detail.target;
    const targetId = target.id || target.getAttribute('data-testid') || target.tagName;
    
    Logger.error('HTMX response error', {
        event: 'htmx:responseError',
        target: targetId,
        method: event.detail.verb,
        url: event.detail.path,
        status: event.detail.xhr.status,
        response_text: event.detail.xhr.responseText?.substring(0, 200), // Truncate
    });
});

// Log HTMX swap events (DOM updates)
document.body.addEventListener('htmx:afterSwap', (event) => {
    const target = event.detail.target;
    const targetId = target.id || target.getAttribute('data-testid') || target.tagName;
    
    Logger.debug('HTMX content swapped', {
        event: 'htmx:afterSwap',
        target: targetId,
        swap_style: event.detail.xhr.getResponseHeader('HX-Reswap'),
    });
});

// Log HTMX validation errors
document.body.addEventListener('htmx:validation:failed', (event) => {
    const target = event.detail.target;
    const targetId = target.id || target.getAttribute('data-testid') || target.tagName;
    
    Logger.warn('HTMX validation failed', {
        event: 'htmx:validation:failed',
        target: targetId,
        form: target.closest('form')?.id,
    });
});
```

### Pattern 3: User Action Logging

Log specific user actions:

```javascript
/**
 * User Action Logging
 * Log important user interactions
 */

// Log button clicks
document.addEventListener('click', (event) => {
    const button = event.target.closest('button, a.btn');
    if (button) {
        const action = button.getAttribute('data-action') || 
                      button.textContent.trim() ||
                      'unknown';
        
        Logger.info('Button clicked', {
            action: action,
            button_id: button.id,
            button_class: button.className,
            test_id: button.getAttribute('data-testid'),
        });
    }
});

// Log form submissions
document.addEventListener('submit', (event) => {
    const form = event.target;
    
    Logger.info('Form submitted', {
        form_id: form.id,
        form_action: form.action,
        form_method: form.method,
        test_id: form.getAttribute('data-testid'),
    });
});

// Log navigation
window.addEventListener('popstate', (event) => {
    Logger.info('Navigation (back/forward)', {
        url: window.location.pathname,
        state: event.state,
    });
});
```

### Pattern 4: JavaScript Error Logging

Catch and log JavaScript errors:

```javascript
/**
 * Global Error Handler
 * Catch unhandled JavaScript errors
 */
window.addEventListener('error', (event) => {
    Logger.error('JavaScript error', {
        message: event.message,
        filename: event.filename,
        line: event.lineno,
        column: event.colno,
        error: event.error?.toString(),
        stack: event.error?.stack,
    });
});

// Catch unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    Logger.error('Unhandled promise rejection', {
        reason: event.reason?.toString(),
        promise: event.promise,
    });
});
```

### Pattern 5: Django Backend Endpoint

Create view to receive frontend logs:

**File**: `{app_name}/views/logging_views.py`

```python
import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# GUI logger (writes to logs/gui.log)
gui_logger = logging.getLogger('gui')

@require_POST
def log_gui_event(request):
    """
    Receive frontend log events and write to gui.log
    
    Expected JSON payload:
    {
        "level": "INFO",
        "timestamp": "2026-04-08T10:30:00.000Z",
        "message": "Button clicked",
        "context": {"button_id": "save-btn"},
        "url": "/playbooks/create/",
        "user_agent": "Mozilla/5.0..."
    }
    """
    try:
        data = json.loads(request.body)
        level = data.get('level', 'INFO').upper()
        message = data.get('message', '')
        context = data.get('context', {})
        url = data.get('url', '')
        user_agent = data.get('user_agent', '')
        
        # Get user info
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        
        # Format log message
        log_message = (
            f"[GUI] {message} | "
            f"url={url} | "
            f"user_id={user_id} | "
            f"context={json.dumps(context)} | "
            f"user_agent={user_agent[:50]}"  # Truncate user agent
        )
        
        # Log at appropriate level
        if level == 'DEBUG':
            gui_logger.debug(log_message)
        elif level == 'INFO':
            gui_logger.info(log_message)
        elif level == 'WARN':
            gui_logger.warning(log_message)
        elif level == 'ERROR':
            gui_logger.error(log_message)
        else:
            gui_logger.info(log_message)
            
        return JsonResponse({'status': 'logged'})
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse GUI log JSON: {e}")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        
    except Exception as e:
        logging.error(f"Failed to log GUI event: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
```

**Add URL route** in `{app_name}/urls.py`:

```python
from django.urls import path
from .views import logging_views

urlpatterns = [
    # ... other URLs ...
    path('api/log/gui/', logging_views.log_gui_event, name='log_gui_event'),
]
```

### Pattern 6: Include Logger in Base Template

Add to `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- ... other head content ... -->
    
    <!-- Logger (load early) -->
    <script src="{% static 'js/logger.js' %}"></script>
</head>
<body>
    <!-- ... body content ... -->
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Initialize logging after HTMX loads -->
    <script>
        // Log page load
        Logger.info('Page loaded', {
            url: window.location.pathname,
            referrer: document.referrer,
        });
    </script>
</body>
</html>
```

### Pattern 7: Conditional Logging (Production vs Development)

Add environment-aware logging:

```javascript
const Logger = {
    // ... existing methods ...
    
    /**
     * Check if we should send logs to backend
     */
    _shouldSendToBackend() {
        // Don't send debug logs in production
        if (this._isProduction() && this.level === 'debug') {
            return false;
        }
        return true;
    },
    
    /**
     * Check if running in production
     */
    _isProduction() {
        return window.location.hostname !== 'localhost' && 
               window.location.hostname !== '127.0.0.1';
    },
    
    _log(level, message, context = {}) {
        // ... existing console logging ...
        
        // Only send to backend if appropriate
        if (this._shouldSendToBackend()) {
            this._sendToBackend(logEntry);
        }
    },
};
```

## Usage Examples

### Example 1: Log User Action

```javascript
// In your template or JavaScript
document.getElementById('save-playbook-btn').addEventListener('click', () => {
    Logger.info('Save playbook button clicked', {
        playbook_id: document.getElementById('playbook-id').value,
        form_valid: document.getElementById('playbook-form').checkValidity(),
    });
});
```

### Example 2: Log HTMX Form Submission

```html
<form hx-post="/playbooks/create/" 
      hx-target="#playbook-list"
      hx-swap="beforeend"
      data-testid="playbook-create-form">
    <!-- Form fields -->
    <button type="submit" data-action="create-playbook">Create</button>
</form>

<script>
// HTMX events are automatically logged by the event listeners
// No additional code needed!
</script>
```

### Example 3: Log Custom Business Logic

```javascript
function validatePlaybookName(name) {
    if (name.length < 3) {
        Logger.warn('Playbook name validation failed', {
            name: name,
            min_length: 3,
            actual_length: name.length,
        });
        return false;
    }
    
    Logger.debug('Playbook name validated', {
        name: name,
        length: name.length,
    });
    return true;
}
```

### Example 4: Log API Call

```javascript
async function fetchPlaybooks() {
    Logger.info('Fetching playbooks', { endpoint: '/api/playbooks/' });
    
    try {
        const response = await fetch('/api/playbooks/');
        const data = await response.json();
        
        Logger.info('Playbooks fetched successfully', {
            count: data.length,
            endpoint: '/api/playbooks/',
        });
        
        return data;
    } catch (error) {
        Logger.error('Failed to fetch playbooks', {
            endpoint: '/api/playbooks/',
            error: error.message,
        });
        throw error;
    }
}
```

## Testing Frontend Logging

### Manual Testing

1. Open browser console
2. Perform actions (click buttons, submit forms)
3. Verify console shows log messages
4. Check `logs/gui.log` for persisted entries

### Automated Testing (Playwright)

```python
# tests/e2e/test_frontend_logging.py
import pytest
from playwright.sync_api import Page

def test_button_click_logs(page: Page):
    """Verify button clicks are logged."""
    # Set up console listener
    console_messages = []
    page.on('console', lambda msg: console_messages.append(msg.text))
    
    # Navigate and click button
    page.goto('/playbooks/')
    page.click('[data-testid="create-playbook-btn"]')
    
    # Verify log message
    assert any('Button clicked' in msg for msg in console_messages)

def test_htmx_request_logs(page: Page):
    """Verify HTMX requests are logged."""
    console_messages = []
    page.on('console', lambda msg: console_messages.append(msg.text))
    
    # Trigger HTMX request
    page.goto('/playbooks/')
    page.fill('[name="search"]', 'test')
    page.wait_for_selector('[hx-trigger="input"]')
    
    # Verify HTMX log messages
    assert any('HTMX request started' in msg for msg in console_messages)
    assert any('HTMX request completed' in msg for msg in console_messages)
```

## Performance Considerations

### Throttling Logs

For high-frequency events (e.g., scroll, mousemove), throttle logging:

```javascript
const Logger = {
    // ... existing methods ...
    
    /**
     * Throttled logging for high-frequency events
     */
    _throttledLogs: new Map(),
    
    throttle(key, message, context, delay = 1000) {
        const now = Date.now();
        const lastLog = this._throttledLogs.get(key);
        
        if (!lastLog || now - lastLog > delay) {
            this.info(message, context);
            this._throttledLogs.set(key, now);
        }
    },
};

// Usage
window.addEventListener('scroll', () => {
    Logger.throttle('scroll', 'User scrolling', {
        scroll_y: window.scrollY,
    });
});
```

### Batching Logs

Send logs in batches to reduce HTTP requests:

```javascript
const Logger = {
    _logQueue: [],
    _batchSize: 10,
    _flushInterval: 5000, // 5 seconds
    
    _sendToBackend(logEntry) {
        this._logQueue.push(logEntry);
        
        if (this._logQueue.length >= this._batchSize) {
            this._flushLogs();
        }
    },
    
    _flushLogs() {
        if (this._logQueue.length === 0) return;
        
        const batch = [...this._logQueue];
        this._logQueue = [];
        
        fetch('/api/log/gui/batch/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this._getCsrfToken(),
            },
            body: JSON.stringify({ logs: batch }),
        }).catch(err => console.error('Failed to send log batch:', err));
    },
};

// Flush logs periodically
setInterval(() => Logger._flushLogs(), Logger._flushInterval);

// Flush on page unload
window.addEventListener('beforeunload', () => Logger._flushLogs());
```

## References

- HTMX Events Documentation: https://htmx.org/events/
- MDN Console API: https://developer.mozilla.org/en-US/docs/Web/API/Console
- Django Logging: https://docs.djangoproject.com/en/stable/topics/logging/

