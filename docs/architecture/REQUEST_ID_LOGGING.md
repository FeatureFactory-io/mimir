# Request ID Logging

## Overview

Every HTTP request to Mimir now gets a unique request ID that's tracked throughout the entire request lifecycle. This makes debugging and tracing much easier.

## What Was Added

### 1. Request ID Middleware (`mimir/middleware.py`)
- Generates a unique UUID for each request
- Preserves a safe `X-Request-ID` from upstream systems: 1–100 letters, digits, periods, underscores or hyphens, beginning with a letter or digit
- Replaces absent, malformed or credential-like IDs with one UUID before request context or logs are published
- Stores request ID on the request object as `request.request_id`
- Returns request ID in response headers as `X-Request-ID`
- Logs request start/end/errors with the safe request ID; request-start attribution uses the server-side actor ID

### 2. Logging Filter (`mimir/logging_filters.py`)
- Adds request ID to every log message
- Shows `NO_REQUEST` for logs outside of HTTP requests (management commands, background tasks)

### 3. Thread-Local Storage (`mimir/request_local.py`)
- Stores current request in thread-local storage
- Allows logging filter to access request ID from anywhere in the codebase
- Defines the pure shared correlation/credential policy without importing Django models during logging startup

## Log Format

All logs now include request ID:

**File logs (verbose):**
```
[2025-11-28 10:30:45] [INFO    ] [REQ:a1b2c3d4-5678-49ab-8cde-0123456789ab] [PID:12345:TID:67890] [accounts/views.py:85] [views.login_view] User maria attempting login
```

**Console logs (simple):**
```
[REQ:a1b2c3d4-5678-49ab-8cde-0123456789ab] INFO User maria logged in successfully
```

## Usage

### In Views

Access the request ID directly from the request object:

```python
def my_view(request):
    request_id = request.request_id
    logger.info("Processing request actor_id=%s", request.user.pk)
    # The log message will automatically include the request ID
```

### For Client-Side Tracking

The response includes the request ID in headers:

```bash
curl -I http://localhost:8000/dashboard/
# Response includes:
# X-Request-ID: a1b2c3d4-5678-49ab-8cde-0123456789ab
```

### Propagating from Upstream

If you have a load balancer or API gateway generating safe request IDs, pass it along:

```bash
curl -H "X-Request-ID: my-custom-tracking-id" http://localhost:8000/api/
# Response will echo back the same ID:
# X-Request-ID: my-custom-tracking-id
```

Unsafe values are never echoed as request IDs. The generated replacement is used by request logs, response headers and the PIP summary interaction. The PIP view reads the validated `request.request_id`; its raw-header fallback remains only for direct callers without middleware. Background records retain `NO_REQUEST`.

### Searching Logs

To trace a specific request through all logs:

```bash
# Find all log entries for a specific request
grep "REQ:a1b2c3d4-5678-49ab-8cde-0123456789ab" logs/app.log

# See the full journey of a request
grep "REQ:a1b2c3d4" logs/app.log | grep -E "(REQUEST_START|REQUEST_END|REQUEST_ERROR)"
```

## Benefits

1. **Easy Debugging**: Follow a single request through multiple log statements
2. **Error Tracking**: When users report errors, ask for the request ID from browser dev tools
3. **Performance Analysis**: Track how long specific requests take
4. **Distributed Tracing**: Compatible with upstream tracing systems
5. **User Support**: Users can provide request ID when reporting issues

## Example Request Flow

```
1. User hits /auth/user/login/
   [REQ:abc-123] [REQUEST_START] GET /auth/user/login/ actor_id=anonymous

2. Login form displayed
   [REQ:abc-123] Displaying login form

3. User submits credentials
   [REQ:def-456] [REQUEST_START] POST /auth/user/login/ actor_id=anonymous
   [REQ:def-456] Login attempt for username: maria, remember_me: True
   [REQ:def-456] User maria logged in with remember me (30 days session)

4. Redirect to dashboard
   [REQ:def-456] [REQUEST_END] POST /auth/user/login/ - Status: 302

5. Dashboard loads
   [REQ:ghi-789] [REQUEST_START] GET /dashboard/ actor_id=42
   [REQ:ghi-789] User maria accessing dashboard
   [REQ:ghi-789] [REQUEST_END] GET /dashboard/ - Status: 200
```

## Configuration

All configuration is in `mimir/settings.py`:

```python
# Middleware order matters - RequestIDMiddleware should be after auth
MIDDLEWARE = [
    ...
    "mimir.middleware.RequestIDMiddleware",
]

# Logging config includes request_id filter
LOGGING = {
    'filters': {
        'request_id': {
            '()': 'mimir.logging_filters.RequestIDFilter',
        },
    },
    'handlers': {
        'file': {
            'filters': ['request_id'],
            ...
        },
    },
}
```

## Testing

Run the request ID integration tests:

```bash
pytest tests/integration/test_request_id_logging.py -v
```

Tests verify:
- Request IDs are generated and returned in headers
- Custom request IDs are propagated
- Each request gets a unique ID
- Request IDs are accessible in views

## Performance Impact

Minimal - adds approximately:
- UUID generation: ~1-2μs per request
- Thread-local storage access: ~0.1μs per log statement
- Header addition: ~0.1μs per request

Total overhead: < 5μs per request (negligible).
