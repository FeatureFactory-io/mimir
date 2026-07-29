"""Views for the methodology app."""
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from methodology.services.global_search_service import (
    GlobalSearchService,
    SEARCH_ENTITY_META,
)
logger = logging.getLogger(__name__)

ACTIVITY_FEED_HOURS_LABELS = {
    1: "Last hour",
    24: "Last 24h",
    168: "Last week",
}


def _parse_activity_feed_hours(request, default=24):
    """Parse and validate Recently Used feed hours from request query params."""
    from methodology.services.activity_service import ActivityService

    raw = request.GET.get("hours", default)
    try:
        hours = int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "dashboard_activities invalid hours=%r; falling back to %s",
            raw,
            default,
        )
        hours = default
    try:
        return ActivityService._validate_feed_hours(hours)
    except ValueError:
        logger.warning(
            "dashboard_activities disallowed hours=%s; falling back to %s",
            hours,
            default,
        )
        return default


def _activity_feed_hours_label(hours):
    """Return UI label for the selected Recently Used time window."""
    return ACTIVITY_FEED_HOURS_LABELS.get(hours, ACTIVITY_FEED_HOURS_LABELS[24])

# ─── NO ORM IN VIEWS ────────────────────────────────────────────────────────
# Views are thin controllers. NEVER query the ORM directly here.
# All data access must go through services in methodology/services/.
# Both views and MCP tools drink from the same service well.
# ────────────────────────────────────────────────────────────────────────────


def index(request):
    """
    Home page - methodology explorer landing page. Public access allowed.

    :param request: Django request object. Example: HttpRequest(method='GET', user=<User: admin>)
    :return: Rendered HTML response. Example: HttpResponse(status=200, content="<div>...</div>")
    """
    return render(request, 'methodology/index.html')


def use_cases(request):
    """
    Public 'What can Mimir do?' page — role-based feature overview. No login required.

    :param request: Django request object.
    :return: Rendered HTML response.
    """
    logger.info("use_cases | user=%s", getattr(request.user, "username", "anonymous"))
    return render(request, 'methodology/use_cases.html')


@login_required
def dashboard(request):
    """
    Dashboard view with activity feed and recent playbooks (FOB-DASHBOARD-1).
    
    Displays user's personalized dashboard with:
    - My Playbooks section (5 most recent playbooks)
    - Recent Activity feed (10 most recent actions)
    - Quick Actions panel
    
    Template: dashboard.html
    Context:
        recent_playbooks: List of recent Playbook objects
        recent_activities: QuerySet of recent Activity objects
        activity_count: Number of recent activities
        playbook_count: Number of recent playbooks
    
    :param request: Django request object. Example: HttpRequest(method='GET', user=<User: maria>)
    :return: Rendered HTML response with dashboard data. Example: HttpResponse(status=200, content="<div>...</div>")
    :raises: None - handles all exceptions gracefully
    """
    logger.info(f"User {request.user.username} accessing dashboard")
    
    try:
        from methodology.services.activity_service import ActivityService
        from methodology.services.playbook_service import PlaybookService
        
        # Get recent playbooks (owned + public + team - last 5 updated)
        owned_playbooks = list(PlaybookService.list_playbooks(author=request.user))
        public_playbooks = list(PlaybookService.list_public_playbooks(request.user))
        team_playbooks = list(PlaybookService.list_team_playbooks_for_user(request.user))
        
        # Combine and deduplicate by playbook ID
        all_playbooks_dict = {}
        for pb in owned_playbooks + public_playbooks + team_playbooks:
            if pb.id not in all_playbooks_dict:
                all_playbooks_dict[pb.id] = pb
        
        # Sort by updated_at, take top 5
        all_playbooks = list(all_playbooks_dict.values())
        recent_playbooks = sorted(all_playbooks, key=lambda p: p.updated_at, reverse=True)[:5]
        
        # Get recent activities (last 10 within default 24h window)
        activity_hours = 24
        recent_activities = ActivityService.get_recent_activities(
            request.user, limit=10, hours=activity_hours
        )
        activity_count_in_window = ActivityService.count_recent_activities_in_window(
            request.user, hours=activity_hours
        )
        
        # Get counts (total unique accessible playbooks)
        playbook_count = len(all_playbooks)
        
        logger.info(
            "Dashboard loaded for %s: %s playbooks, activity_count_in_window=%s hours=%s",
            request.user.username,
            playbook_count,
            activity_count_in_window,
            activity_hours,
        )
        
        return render(request, 'dashboard.html', {
            'recent_playbooks': recent_playbooks,
            'recent_activities': recent_activities,
            'activity_count_in_window': activity_count_in_window,
            'activity_hours': activity_hours,
            'activity_hours_label': _activity_feed_hours_label(activity_hours),
            'playbook_count': playbook_count,
        })
        
    except Exception as e:
        logger.error(f"Error loading dashboard for {request.user.username}: {e}")
        # Return dashboard with empty data rather than error page
        return render(request, 'dashboard.html', {
            'recent_playbooks': [],
            'recent_activities': [],
            'activity_count_in_window': 0,
            'activity_hours': 24,
            'activity_hours_label': _activity_feed_hours_label(24),
            'playbook_count': 0,
            'error_message': 'Unable to load some dashboard data'
        })


@login_required
def dashboard_activities(request):
    """
    HTMX endpoint for refreshing activity feed.
    
    Returns updated activity feed HTML fragment.
    
    Args:
        request: Django request object with optional 'hours' parameter
        
    Returns:
        HttpResponse: HTML fragment for activity feed
        
    Example:
        GET /dashboard/activities/?hours=24
    """
    logger.info(f"User {request.user.username} requested activity feed refresh")
    
    try:
        from methodology.services.activity_service import ActivityService
        
        hours = _parse_activity_feed_hours(request)
        logger.info(
            "dashboard_activities entry user=%s hours=%s",
            request.user.username,
            hours,
        )
        
        recent_activities = ActivityService.get_recent_activities(
            request.user, limit=10, hours=hours
        )
        activity_count_in_window = ActivityService.count_recent_activities_in_window(
            request.user, hours=hours
        )
        
        logger.info(
            "Returned %s activities for %s (hours=%s)",
            len(recent_activities),
            request.user.username,
            hours,
        )
        
        return render(request, 'methodology/partials/activity_feed_refresh.html', {
            'recent_activities': recent_activities,
            'activity_count_in_window': activity_count_in_window,
            'activity_hours': hours,
            'activity_hours_label': _activity_feed_hours_label(hours),
        })
        
    except Exception as e:
        logger.error(f"Error refreshing activity feed for {request.user.username}: {e}")
        return render(request, 'methodology/partials/activity_feed_refresh.html', {
            'recent_activities': [],
            'activity_count_in_window': 0,
            'activity_hours': 24,
            'activity_hours_label': _activity_feed_hours_label(24),
        })


@login_required
def global_search(request):
    """Global search view for NAV-06.

    Delegates search logic to GlobalSearchService and renders consolidated
    results across Playbooks, Workflows, and Activities.
    
    Template: search/results.html
    Context:
        query: str - Search query entered by user
        playbooks: List[Playbook] - Matching playbooks
        workflows: List[Workflow] - Matching workflows
        activities: List[Activity] - Matching activities
        type_filter: str - Active type filter (playbooks/workflows/activities)
        status_filter: str - Active status filter (draft/active/released/disabled)
        source_filter: str - Active source filter (owned/downloaded)
    
    :param request: Django HttpRequest with GET parameters q, type, status, source
    :return: HttpResponse with rendered search results template
    """

    query = request.GET.get("q", "").strip()
    type_filter = (request.GET.get("type") or "").strip()
    valid_keys = {m["key"] for m in SEARCH_ENTITY_META}
    if type_filter and type_filter not in valid_keys:
        type_filter = ""

    filters = {"type": type_filter} if type_filter else {}

    logger.info(
        "Global search requested by %s with query='%s', type=%s",
        request.user.username,
        query,
        type_filter or "all",
    )

    service = GlobalSearchService()
    results = service.search(query=query, user=request.user, filters=filters)
    sections, total_count = service.build_sections(query, results, type_filter)

    logger.info(
        "Global search completed for %s with query='%s': %d total matches",
        request.user.username,
        query,
        total_count,
    )

    type_choices = [{"value": "", "label": "All types"}] + [
        {"value": m["key"], "label": m["label"]} for m in SEARCH_ENTITY_META
    ]

    return render(
        request,
        "search/results.html",
        {
            "query": query,
            "sections": sections,
            "total_count": total_count,
            "type_filter": type_filter,
            "type_choices": type_choices,
            "show_no_query_prompt": not query,
            "show_empty_state": bool(query) and total_count == 0,
        },
    )


@login_required
def global_search_suggestions(request):
    """Return HTML fragment with live global search suggestions.

    Designed for HTMX / AJAX usage from the navbar search input.
    
    Template: search/partials/suggestions.html
    Context:
        query: str - Search query entered by user
        playbooks: List[Playbook] - Top 5 matching playbooks
        workflows: List[Workflow] - Top 5 matching workflows
        activities: List[Activity] - Top 5 matching activities
    
    :param request: Django HttpRequest with GET parameter q
    :return: HttpResponse with rendered suggestions fragment
    """

    query = (request.GET.get("q", "") or "").strip()
    if not query:
        logger.info(
            "Global search suggestions requested by %s with empty query - returning empty fragment",
            request.user.username,
        )
        return render(
            request,
            "search/partials/suggestions.html",
            {"query": "", "sections": [], "total_count": 0},
        )

    logger.info(
        "Global search suggestions requested by %s with query='%s'",
        request.user.username,
        query,
    )

    service = GlobalSearchService()
    results = service.search(query=query, user=request.user, filters=None)
    sections, total_count = service.build_sections(query, results, type_filter="")
    limited_sections = []
    for section in sections:
        limited = dict(section)
        limited["items"] = section["items"][:5]
        limited["count"] = len(section["items"])
        limited_sections.append(limited)

    logger.info(
        "Global search suggestions for %s with query='%s': %d total matches (limited per type)",
        request.user.username,
        query,
        total_count,
    )

    return render(
        request,
        "search/partials/suggestions.html",
        {
            "query": query,
            "sections": limited_sections,
            "total_count": total_count,
        },
    )
