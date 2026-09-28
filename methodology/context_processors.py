"""Context processors for methodology app.

Injects global context variables into all template contexts.
"""

import logging

from django.urls import reverse

from methodology.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

ACTIVE_REALM = "mimir"
REALM_ITEMS = (
    {
        "slug": "featurefactory",
        "label": "FeatureFactory",
        "url": "https://featurefactory.io",
        "external": False,
        "tooltip": "FeatureFactory home",
        "mark": "images/realm/featurefactory.png",
    },
    {
        "slug": "mimir",
        "label": "Mimir",
        "url": "/",
        "external": False,
        "tooltip": "Mimir — engineering playbooks (this app)",
        "mark": "images/realm/mimir.png",
    },
    {
        "slug": "huginn",
        "label": "Huginn",
        "url": "https://huginn.featurefactory.io",
        "external": False,
        "tooltip": "Huginn",
        "mark": "images/realm/huginn.jpg",
    },
    {
        "slug": "yggdrasil",
        "label": "Yggdrasil",
        "url": "https://yggdrasil.featurefactory.io",
        "external": False,
        "tooltip": "Yggdrasil",
        "mark": "images/realm/yggdrasil.png",
    },
    {
        "slug": "heimdall",
        "label": "Heimdall",
        "url": "https://heimdall.featurefactory.io",
        "external": False,
        "tooltip": "Heimdall",
        "mark": "",
    },
)


def app_version(request):
    """Inject application version information.

    :param request: Django HTTP request.
    :returns: Empty dict (version injected via other means).
    """
    return {}


def pip_nav(request):
    """Inject PIP navigation badge count for unread PIPs.

    :param request: Django HTTP request.
    :returns: Dict with pip_nav_unread_count key.
    """
    if request.user.is_authenticated:
        from methodology.models import ProcessImprovementProposal

        unread_count = ProcessImprovementProposal.objects.filter(
            status=ProcessImprovementProposal.STATUS_SUBMITTED
        ).count()
        return {"pip_nav_unread_count": unread_count}
    return {"pip_nav_unread_count": 0}


def primary_nav_section(request):
    """Inject realm bar and app sidebar context for the FOB shell.

    :param request: Django HTTP request. Example: GET /playbooks/
    :return: Shell dict. Example: {"nav_section": "playbooks", "chrome": "authenticated"}
    """
    logger.info("primary_nav_section entry path=%s", request.path)
    return build_shell_context(request)


def build_shell_context(request) -> dict:
    """Build realm items, sidebar sections, and guest or authenticated chrome.

    :param request: Django HTTP request. Example: GET /
    :return: Shell dict. Example: {"active_realm": "mimir", "chrome": "guest", "nav_section": "none"}
    """
    section = _resolve_nav_section(request.path)
    chrome = _chrome_for(request)
    logger.info("primary_nav_section branch chrome=%s", chrome)
    logger.info(
        "primary_nav_section exit nav_section=%s",
        section or "none",
    )
    return {
        "nav_section": section,
        "chrome": chrome,
        "active_realm": ACTIVE_REALM,
        "realm_items": list(REALM_ITEMS),
        "sidebar_sections": _sidebar_sections(),
    }


def _chrome_for(request) -> str:
    """Return guest or authenticated chrome for the request.

    :param request: Django HTTP request. Example: GET /dashboard/
    :return: chrome label. Example: "guest"
    """
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return "authenticated"
    return "guest"


def _sidebar_sections() -> list:
    """Return Workspace, Methodology, and Collaborate sidebar groups.

    :return: Section list. Example: [{"id": "workspace", "label": "Workspace", "items": [...]}]
    """
    return [
        _section("workspace", "Workspace", [_home_item()]),
        _section("methodology", "Methodology", _methodology_items()),
        _section("collaborate", "Collaborate", _collaborate_items()),
    ]


def _section(section_id: str, label: str, items: list) -> dict:
    """Wrap sidebar links in a labeled group.

    :param section_id: Group id. Example: "methodology"
    :param label: Visible heading. Example: "Methodology"
    :param items: Link dicts. Example: [{"slug": "playbooks", "testid": "nav-playbooks"}]
    :return: Section dict. Example: {"id": "methodology", "label": "Methodology", "items": [...]}
    """
    return {"id": section_id, "label": label, "items": items}


def _home_item() -> dict:
    """Return the Home sidebar link.

    :return: Link dict. Example: {"slug": "home", "url": "/dashboard/", "testid": "nav-dashboard"}
    """
    return _link(
        "home",
        "Home",
        "/dashboard/",
        "nav-dashboard",
        "fas fa-gauge",
        "Overview and key metrics (dashboard)",
    )


def _methodology_items() -> list:
    """Return methodology entity links in sidebar order.

    :return: Link dicts. Example: [{"slug": "playbooks", "testid": "nav-playbooks"}]
    """
    return [
        _link("playbooks", "Playbooks", "/playbooks/", "nav-playbooks", "fas fa-book-sparkles", "Browse and manage your engineering playbooks"),
        _link("workflows", "Workflows", reverse("workflow_global_list"), "nav-workflows", "fas fa-diagram-project", "View all workflows across your playbooks"),
        _link("phases", "Phases", reverse("phase_list_global"), "nav-phases", "fas fa-bars-progress", "View all phases across your playbooks"),
        _link("activities", "Activities", reverse("activity_global_list"), "nav-activities", "fas fa-list-check", "View all activities across your playbooks and workflows"),
        _link("artifacts", "Artifacts", reverse("artifact_list_global"), "nav-artifacts", "fas fa-gift", "View all artifacts across your playbooks"),
        _link("agents", "Agents", reverse("agent_list"), "nav-agents", "fas fa-brain-circuit", "View all agents across your playbooks"),
        _link("skills", "Skills", reverse("skill_list"), "nav-skills", "fas fa-hand-holding-magic", "View all skills across your playbooks"),
        _link("rules", "Rules", reverse("rule_list"), "nav-rules", "fas fa-scale-balanced", "View all IDE rules across your playbooks"),
    ]


def _collaborate_items() -> list:
    """Return Teams and PIPs sidebar links.

    :return: Link dicts. Example: [{"slug": "teams", "url": "/teams/"}]
    """
    return [
        _link("teams", "Teams", "/teams/", "nav-teams", "fas fa-users", "Browse and manage teams"),
        _link("pips", "PIPs", reverse("pip_list"), "nav-pips", "fas fa-lightbulb", "Playbook Improvement Proposals"),
    ]


def _link(slug: str, label: str, url: str, testid: str, icon: str, tooltip: str) -> dict:
    """Build one sidebar link.

    :param slug: Active-item key. Example: "playbooks"
    :param label: Visible text. Example: "Playbooks"
    :param url: Destination. Example: "/playbooks/"
    :param testid: data-testid. Example: "nav-playbooks"
    :param icon: Font Awesome classes. Example: "fas fa-book-sparkles"
    :param tooltip: Hover text. Example: "Browse and manage your engineering playbooks"
    :return: Link dict. Example: {"slug": "playbooks", "testid": "nav-playbooks"}
    """
    return {
        "slug": slug,
        "label": label,
        "url": url,
        "testid": testid,
        "icon": icon,
        "tooltip": tooltip,
    }


def _resolve_nav_section(path: str):
    """Return nav section string for ``path``, or ``None`` if no match.

    More specific entity paths win over playbook nesting so e.g.
    ``/playbooks/12/workflows/25/activities/129/`` highlights Activities,
    and ``/playbooks/12/phases/`` highlights Phases — not Playbooks.

    Dashboard is checked before the generic ``/activities/`` substring so
    ``/dashboard/activities/`` stays on Home.

    :param path: URL path string.
    :returns: Section identifier or ``None``.
    """
    if path.startswith("/dashboard/"):
        return "home"
    if path.startswith("/browser/"):
        return "playbooks"
    if path.startswith("/teams/"):
        return "teams"
    if path.startswith("/pips/") or path.startswith("/pip/"):
        return "pips"

    # Nested or global entity routes (before bare /playbooks/)
    if "/activities/" in path or path.startswith("/activities/"):
        return "activities"
    if "/workflows/" in path or path.startswith("/workflows/"):
        return "workflows"
    if "/phases/" in path or path.startswith("/phases/"):
        return "phases"
    if "/artifacts/" in path or path.startswith("/artifacts/"):
        return "artifacts"
    if "/agents/" in path or path.startswith("/agents/"):
        return "agents"
    if "/skills/" in path or path.startswith("/skills/"):
        return "skills"
    if "/rules/" in path or path.startswith("/rules/"):
        return "rules"

    if path.startswith("/playbooks/"):
        return "playbooks"
    return None


def notification_count(request):
    """Inject unread notification count for authenticated users.

    :param request: Django HTTP request.
    :returns: Dict with unread_notification_count key.
    """
    if request.user.is_authenticated:
        count = NotificationService.get_unread_count(request.user)
        return {"unread_notification_count": count}
    return {"unread_notification_count": 0}
