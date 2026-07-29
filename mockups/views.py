import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_STATUS_CSS = {
    "Draft": "bg-secondary",
    "Submitted": "bg-primary",
    "Processing (Galdr)": "bg-warning text-dark",
    "Reviewed": "pip-status-reviewed",
    "Accepted": "bg-success",
    "Rejected": "bg-danger",
}

_CHANGE_TYPE_CSS = {
    "ADD": "bg-success",
    "ALTER": "bg-warning text-dark",
    "DROP": "bg-danger",
}

MOCK_PIPS = [
    {
        "id": 42,
        "title": "Add Accessibility Audit",
        "target_playbook": "React Frontend Dev",
        "target_playbook_id": 1,
        "target_version": "v1.0",
        "changes_count": 1,
        "status": "Reviewed",
        "status_css": _STATUS_CSS["Reviewed"],
        "submitted": "2026-05-14",
        "last_updated": "2026-05-15",
        "submitted_by": "maria",
        "status_changed": True,
    },
    {
        "id": 38,
        "title": "State Management Patterns",
        "target_playbook": "React Frontend Dev",
        "target_playbook_id": 1,
        "target_version": "v1.0",
        "changes_count": 2,
        "status": "Accepted",
        "status_css": _STATUS_CSS["Accepted"],
        "submitted": "2026-04-20",
        "last_updated": "2026-04-22",
        "submitted_by": "maria",
        "status_changed": False,
    },
    {
        "id": 35,
        "title": "Drop Legacy IE Support",
        "target_playbook": "React Frontend Dev",
        "target_playbook_id": 1,
        "target_version": "v1.0",
        "changes_count": 1,
        "status": "Rejected",
        "status_css": _STATUS_CSS["Rejected"],
        "submitted": "2026-04-10",
        "last_updated": "2026-04-11",
        "submitted_by": "maria",
        "status_changed": False,
    },
    {
        "id": 30,
        "title": "Add Figma Integration Activity",
        "target_playbook": "UX Research",
        "target_playbook_id": 2,
        "target_version": "v2.1",
        "changes_count": 3,
        "status": "Draft",
        "status_css": _STATUS_CSS["Draft"],
        "submitted": "2026-03-05",
        "last_updated": "2026-03-05",
        "submitted_by": "maria",
        "status_changed": False,
    },
    {
        "id": 28,
        "title": "Improve Onboarding Flow",
        "target_playbook": "UX Research",
        "target_playbook_id": 2,
        "target_version": "v2.1",
        "changes_count": 1,
        "status": "Submitted",
        "status_css": _STATUS_CSS["Submitted"],
        "submitted": "2026-03-01",
        "last_updated": "2026-03-01",
        "submitted_by": "maria",
        "status_changed": False,
    },
    {
        "id": 27,
        "title": "Rename Discovery Activity",
        "target_playbook": "UX Research",
        "target_playbook_id": 2,
        "target_version": "v2.1",
        "changes_count": 1,
        "status": "Processing (Galdr)",
        "status_css": _STATUS_CSS["Processing (Galdr)"],
        "submitted": "2026-02-28",
        "last_updated": "2026-02-28",
        "submitted_by": "maria",
        "status_changed": False,
    },
]

MOCK_PIP_42 = {
    "id": 42,
    "title": "Add Accessibility Audit",
    "summary": "The React Frontend Dev playbook lacks WCAG 2.1 AA coverage. "
               "All components we build need accessibility checks but the playbook "
               "currently has no dedicated activity for it.",
    "target_playbook": "React Frontend Dev",
    "target_version": "v1.0",
    "target_playbook_id": 1,
    "status": "Reviewed",
    "status_css": _STATUS_CSS["Reviewed"],
    "submitted_by": "Maria Rodriguez",
    "submitted_at": "2026-05-14 09:00",
    "last_updated": "2026-05-15 08:00",
    "changes": [
        {
            "number": 1,
            "change_type": "ADD",
            "change_type_css": _CHANGE_TYPE_CSS["ADD"],
            "entity_type": "Activity",
            "name": "Accessibility Audit",
            "target_id": None,
            "target_name": None,
            "position": "After: Component Testing (id=22)",
            "content": (
                "Ensure all React components meet WCAG 2.1 AA standards.\n\n"
                "**Setup:** Install `axe-core` and `jest-axe`.\n\n"
                "**Tests:** Add `@axe-core/react` checks to each component's test suite. "
                "Configure the CI/CD pipeline to fail on any accessibility violation.\n\n"
                "**Checklist:**\n"
                "- [ ] All interactive elements keyboard-accessible\n"
                "- [ ] ARIA labels on icon-only buttons\n"
                "- [ ] Colour contrast ≥ 4.5:1\n"
                "- [ ] Focus trap in modals"
            ),
            "galdr_recommendation": "ACCEPT",
            "galdr_reasoning": (
                "Consistent with the Testing & Documentation workflow goal. "
                "No upstream or downstream conflicts detected. "
                "The new activity has a clear, well-defined position in the workflow."
            ),
            "admin_decision": None,
        },
        {
            "number": 2,
            "change_type": "ALTER",
            "change_type_css": _CHANGE_TYPE_CSS["ALTER"],
            "entity_type": "Activity",
            "name": None,
            "target_id": 22,
            "target_name": "Component Testing",
            "position": None,
            "content": (
                "Add `axe-core` a11y tests alongside existing Jest unit tests. "
                "Fail the build on any a11y violation reported by `jest-axe`. "
                "Update the Artifact link to include the new 'a11y-test-report' output."
            ),
            "galdr_recommendation": "REJECT",
            "galdr_reasoning": (
                "The proposed content removes the existing Artifact link to 'Test Suite', "
                "breaking the artifact dependency chain for Workflow 'Testing & Documentation'. "
                "Recommend rejecting until the author preserves the existing artifact link "
                "and appends the new one."
            ),
            "admin_decision": None,
        },
    ],
}

MOCK_PIP_30 = {
    "id": 30,
    "title": "Add Figma Integration Activity",
    "summary": "Our UX Research playbook covers discovery and testing but has no guidance "
               "on Figma handoff. This PIP adds three activities covering design token export, "
               "handoff checklist, and developer review session.",
    "target_playbook": "UX Research",
    "target_version": "v2.1",
    "target_playbook_id": 2,
    "status": "Draft",
    "status_css": _STATUS_CSS["Draft"],
    "submitted_by": "Maria Rodriguez",
    "submitted_at": None,
    "last_updated": "2026-03-05",
    "changes": [
        {
            "number": 1,
            "change_type": "ADD",
                "change_type_css": _CHANGE_TYPE_CSS["ADD"],
                "entity_type": "Activity",
                "name": "Export Design Tokens",
            "target_id": None,
            "target_name": None,
            "position": "Append at end of Workflow: Design Delivery",
            "content": "Export all design tokens from Figma using the Figma Tokens plugin.",
            "galdr_recommendation": None,
            "galdr_reasoning": None,
            "admin_decision": None,
        },
        {
            "number": 2,
            "change_type": "ADD",
                "change_type_css": _CHANGE_TYPE_CSS["ADD"],
                "entity_type": "Activity",
                "name": "Figma Handoff Checklist",
            "target_id": None,
            "target_name": None,
            "position": "After: Export Design Tokens",
            "content": "Run through the 12-item Figma handoff checklist before dev handoff.",
            "galdr_recommendation": None,
            "galdr_reasoning": None,
            "admin_decision": None,
        },
        {
            "number": 3,
            "change_type": "ALTER",
                "change_type_css": _CHANGE_TYPE_CSS["ALTER"],
                "entity_type": "Workflow",
            "name": None,
            "target_id": 5,
            "target_name": "Design Delivery",
            "position": None,
            "content": "Update workflow description to include Figma as the primary design tool.",
            "galdr_recommendation": None,
            "galdr_reasoning": None,
            "admin_decision": None,
        },
    ],
}

MOCK_PIP_38_ADMIN = {
    "id": 38,
    "title": "State Management Patterns",
    "summary": "Adds Redux Toolkit setup and patterns as a dedicated activity, "
               "and updates the existing Component Testing activity to cover store integration testing.",
    "target_playbook": "React Frontend Dev",
    "target_version": "v1.0",
    "target_playbook_id": 1,
    "status": "Reviewed",
    "status_css": _STATUS_CSS["Reviewed"],
    "submitted_by": "Maria Rodriguez",
    "submitted_at": "2026-04-20 14:30",
    "last_updated": "2026-04-21 10:00",
    "changes": [
        {
            "number": 1,
            "change_type": "ADD",
            "change_type_css": _CHANGE_TYPE_CSS["ADD"],
            "entity_type": "Activity",
            "name": "Redux Setup & Patterns",
            "target_id": None,
            "target_name": None,
            "position": "After: Create Components (id=21)",
            "content": (
                "Set up Redux Toolkit. Configure the store. "
                "Define typed hooks (useAppDispatch, useAppSelector). "
                "Document slice pattern and async thunk pattern."
            ),
            "galdr_recommendation": "ACCEPT",
            "galdr_reasoning": (
                "Directly addresses a known gap in the Component Development workflow. "
                "No conflicts with existing activities or artifacts."
            ),
            "admin_decision": "ACCEPT",
        },
        {
            "number": 2,
            "change_type": "ALTER",
            "change_type_css": _CHANGE_TYPE_CSS["ALTER"],
            "entity_type": "Activity",
            "name": None,
            "target_id": 22,
            "target_name": "Component Testing",
            "position": None,
            "content": (
                "Extend Component Testing to cover Redux store integration. "
                "Add section: 'Testing connected components with mock stores using @reduxjs/toolkit'."
            ),
            "galdr_recommendation": "ACCEPT",
            "galdr_reasoning": (
                "Augments existing activity without removing anything. "
                "Artifact links are preserved."
            ),
            "admin_decision": "ACCEPT",
        },
    ],
}


MOCK_PROFILE = {
    "first_name": "Denis",
    "last_name": "Petelin",
    "email": "dpetelin@gmail.com",
    "username": "dpetelin",
    "email_verified": True,   # toggle to False to see unverified state
    "api_token": "mimir_a8f3d9e2b1c4567890abcdef12345678",
    "pips": [
        {
            "pk": 42,
            "title": "Add Accessibility Audit",
            "playbook_name": "React Frontend Dev",
            "status_display": "Submitted",
            "status_css": _STATUS_CSS["Submitted"],
        },
        {
            "pk": 38,
            "title": "State Management Patterns",
            "playbook_name": "React Frontend Dev",
            "status_display": "Accepted",
            "status_css": _STATUS_CSS["Accepted"],
        },
        {
            "pk": 30,
            "title": "Add Figma Integration Activity",
            "playbook_name": "UX Research",
            "status_display": "Draft",
            "status_css": _STATUS_CSS["Draft"],
        },
    ],
    "playbooks": [
        {"pk": 1, "name": "React Frontend Development", "version": "1.0", "status_display": "Released", "status_css": "bg-success"},
        {"pk": 2, "name": "UX Research", "version": "2.1", "status_display": "Released", "status_css": "bg-success"},
        {"pk": 5, "name": "Agile Sprint Retrospectives", "version": "0.3", "status_display": "Draft", "status_css": "bg-secondary"},
    ],
}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def pip_list(request):
    """FOB-PIP-LIST-1: My PIPs with filter bar, status badges, count pill."""
    logger.info("Mockup: pip_list | user=%s", getattr(request.user, "username", "anonymous"))
    statuses = list(_STATUS_CSS.items())
    context = {
        "pips": MOCK_PIPS,
        "pip_count": len(MOCK_PIPS),
        "unread_count": sum(1 for p in MOCK_PIPS if p["status_changed"]),
        "playbooks": ["React Frontend Dev", "UX Research"],
        "statuses": statuses,
        "is_admin": getattr(request.user, "is_staff", False),
        "active_page": "pips",
    }
    return render(request, "mockups/pips/list.html", context)


def pip_create(request):
    """FOB-PIP-CREATE-1: Create PIP with structured Change list."""
    logger.info("Mockup: pip_create | user=%s", getattr(request.user, "username", "anonymous"))
    context = {
        "target_playbook": "React Frontend Dev",
        "target_version": "v1.0",
        "target_playbook_id": 1,
        "released_playbooks": [
            {"id": 1, "name": "React Frontend Dev", "version": "v1.0"},
            {"id": 2, "name": "UX Research", "version": "v2.1"},
        ],
        "entity_types": ["Workflow", "Activity", "Skill", "Agent", "Artifact"],
        "change_types": ["ADD", "ALTER", "DROP"],
        "activities": [
            {"id": 20, "name": "Setup Project", "workflow": "Component Development"},
            {"id": 21, "name": "Create Components", "workflow": "Component Development"},
            {"id": 22, "name": "Component Testing", "workflow": "Testing & Documentation"},
            {"id": 23, "name": "Write Documentation", "workflow": "Testing & Documentation"},
        ],
        "workflows": [
            {"id": 10, "name": "Component Development"},
            {"id": 11, "name": "Testing & Documentation"},
        ],
        "draft_changes": [
            {
                "number": 1,
                "change_type": "ADD",
                "change_type_css": _CHANGE_TYPE_CSS["ADD"],
                "entity_type": "Activity",
                "name": "Accessibility Audit",
                "position": "After: Component Testing (id=22)",
                "content": "Ensure React components meet WCAG 2.1 AA standards…",
            }
        ],
        "active_page": "pips",
    }
    return render(request, "mockups/pips/create.html", context)


def pip_detail(request, pip_id):
    """FOB-PIP-DETAIL-1: View a PIP with Galdr recommendations."""
    logger.info("Mockup: pip_detail | pip_id=%s | user=%s", pip_id, getattr(request.user, "username", "anonymous"))
    pip = MOCK_PIP_30 if pip_id == 30 else MOCK_PIP_42
    context = {
        "pip": pip,
        "active_page": "pips",
    }
    return render(request, "mockups/pips/detail.html", context)


_LOGIN_STATES = {
    "post-register": "Post-registration — check inbox",
    "unverified":    "Login refused — email not verified",
    "email-changed": "Login refused — email changed, re-verification required",
    "normal":        "Normal",
}


def auth_register(request):
    """FOB-LOCAL-USER-CREATE-01: Registration form with ToS checkbox."""
    logger.info("Mockup: auth_register | user=%s", getattr(request.user, "username", "anonymous"))
    return render(request, "mockups/auth/register.html", {})


def auth_login(request):
    """FOB-AUTH-LOGIN-1: Login page — three states driven by ?state= query param.

    States:
      (none / normal)   Plain login form.
      post-register     Info banner: "check your inbox".
      unverified        Warning banner: login refused + re-send link.
      email-changed     Warning banner: email updated, re-verify to log in + re-send link.
    """
    state = request.GET.get("state", "normal")
    if state not in _LOGIN_STATES:
        state = "normal"
    logger.info("Mockup: auth_login | state=%s | user=%s", state, getattr(request.user, "username", "anonymous"))
    return render(request, "mockups/auth/login.html", {
        "state": state,
        "state_label": _LOGIN_STATES[state],
        "prefill_username": request.GET.get("username", ""),
    })


def profile_view(request):
    """FOB-PROFILE-VIEW-1: My profile — account fields, API token, PIPs, playbooks, teams.

    Toggle MOCK_PROFILE["email_verified"] to preview the unverified state.
    Add ?unverified=1 to the URL to force the unverified state in the browser.
    """
    logger.info("Mockup: profile_view | user=%s", getattr(request.user, "username", "anonymous"))
    ctx = dict(MOCK_PROFILE)
    if request.GET.get("unverified"):
        ctx["email_verified"] = False
        logger.info("Mockup: profile_view forcing unverified state via ?unverified=1")
    ctx["teams"] = [t for t in MOCK_TEAMS if t["maria_role"]]
    return render(request, "mockups/profile/view.html", ctx)


def profile_edit(request):
    """FOB-PROFILE-EDIT-1 (account fields): Edit first name, last name, email."""
    logger.info("Mockup: profile_edit | user=%s", getattr(request.user, "username", "anonymous"))
    return render(request, "mockups/profile/edit.html", {**MOCK_PROFILE, "errors": {}})


def use_cases(request):
    """Public landing page — 'What can Mimir do for you?' role overview."""
    logger.info("Mockup: use_cases | user=%s", getattr(request.user, "username", "anonymous"))
    return render(request, "mockups/use-cases/index.html", {})


def pip_admin_review(request, pip_id):
    """FOB-PIP-ADMIN-1: Admin reviews Galdr recommendations and makes decisions."""
    logger.info("Mockup: pip_admin_review | pip_id=%s | user=%s", pip_id, getattr(request.user, "username", "anonymous"))
    context = {
        "pip": MOCK_PIP_38_ADMIN,
        "active_page": "pips",
    }
    return render(request, "mockups/pips/admin_review.html", context)


# ---------------------------------------------------------------------------
# Teams — mock data
# ---------------------------------------------------------------------------

MOCK_TEAMS = [
    {
        "id": 1,
        "name": "Usability",
        "description": "Best practices for usable software development",
        "visibility": "Public",
        "visibility_css": "bg-success",
        "join_policy": "Auto-approve",
        "category": "Engineering",
        "member_count": 127,
        "playbook_count": 8,
        "admin": "Mike Chen",
        "admin_username": "mchen",
        "maria_role": None,  # non-member
    },
    {
        "id": 2,
        "name": "UX",
        "description": "User Experience methodologies and best practices",
        "visibility": "Public",
        "visibility_css": "bg-success",
        "join_policy": "Requires Approval",
        "category": "Design",
        "member_count": 3,
        "playbook_count": 2,
        "admin": "Maria Rodriguez",
        "admin_username": "maria",
        "maria_role": "admin",
    },
    {
        "id": 3,
        "name": "Front-End Guild",
        "description": "JavaScript, CSS, and frontend architecture methodologies",
        "visibility": "Public",
        "visibility_css": "bg-success",
        "join_policy": "Auto-approve",
        "category": "Engineering",
        "member_count": 45,
        "playbook_count": 3,
        "admin": "Tom Lee",
        "admin_username": "tlee",
        "maria_role": "member",
    },
    {
        "id": 4,
        "name": "Acme, INC",
        "description": "UX Consulting services for Acme Corporation",
        "visibility": "Hidden",
        "visibility_css": "bg-secondary",
        "join_policy": "Invite Only",
        "category": "Private",
        "member_count": 5,
        "playbook_count": 1,
        "admin": "Maria Rodriguez",
        "admin_username": "maria",
        "maria_role": "admin",
    },
]

_MOCK_TEAMS_BY_ID = {t["id"]: t for t in MOCK_TEAMS}

MOCK_TEAM_PLAYBOOKS = {
    1: [
        {"id": 10, "name": "React Frontend Development", "version": "1.2", "status": "released"},
        {"id": 11, "name": "Accessible Design Patterns", "version": "0.9", "status": "draft"},
        {"id": 12, "name": "Component Testing Patterns", "version": "2.0", "status": "released"},
    ],
    2: [
        {"id": 13, "name": "UX Research Methods", "version": "1.0", "status": "released"},
        {"id": 14, "name": "Product Discovery Framework", "version": "1.1", "status": "released"},
    ],
    3: [
        {"id": 15, "name": "JavaScript Architecture", "version": "3.0", "status": "released"},
        {"id": 16, "name": "CSS Methodology Guide", "version": "2.1", "status": "released"},
        {"id": 17, "name": "Frontend Performance", "version": "1.0", "status": "released"},
    ],
    4: [
        {"id": 18, "name": "Acme Design System", "version": "1.0", "status": "released"},
    ],
}

MOCK_TEAM_MEMBERS = {
    1: [
        {"name": "Mike Chen", "username": "mchen", "role": "Admin", "joined": "2025-01-10"},
        {"name": "Alice Roy", "username": "aroy", "role": "member", "joined": "2025-02-14"},
        {"name": "Bob Tan", "username": "btan", "role": "member", "joined": "2025-03-01"},
        {"name": "Sara Kim", "username": "skim", "role": "member", "joined": "2025-04-08"},
        {"name": "James Wu", "username": "jwu", "role": "member", "joined": "2025-05-22"},
    ],
    2: [
        {"name": "Maria Rodriguez", "username": "maria", "role": "Admin", "joined": "2025-06-01"},
        {"name": "Mike Chen", "username": "mchen", "role": "member", "joined": "2025-07-15"},
        {"name": "Tom Lee", "username": "tlee", "role": "member", "joined": "2025-08-20"},
    ],
    3: [
        {"name": "Tom Lee", "username": "tlee", "role": "Admin", "joined": "2025-01-05"},
        {"name": "Maria Rodriguez", "username": "maria", "role": "member", "joined": "2025-09-03"},
        {"name": "Alice Roy", "username": "aroy", "role": "member", "joined": "2025-10-11"},
    ],
    4: [
        {"name": "Maria Rodriguez", "username": "maria", "role": "Admin", "joined": "2026-01-01"},
        {"name": "Client A", "username": "client_a", "role": "member", "joined": "2026-01-15"},
    ],
}

MOCK_JOIN_REQUESTS = [
    {"name": "Alice Roy", "username": "aroy", "requested_at": "2026-05-19 10:00", "source": "self"},
    {"name": "Bob Tan", "username": "btan", "requested_at": "2026-05-20 08:30", "source": "invited"},
    {"name": "Sara Kim", "username": "skim", "requested_at": "2026-05-24 14:22", "source": "invited_new"},
]

MOCK_CATEGORIES = ["Engineering", "Design", "Research", "Product", "Private", "Other"]


# ---------------------------------------------------------------------------
# Teams — views
# ---------------------------------------------------------------------------

def teams_browse(request):
    """FOB-TEAMS-BROWSE-1: Browse, search, and filter available teams."""
    logger.info("Mockup: teams_browse | user=%s", getattr(request.user, "username", "anonymous"))
    public_and_member_teams = [t for t in MOCK_TEAMS if t["visibility"] == "Public" or t["maria_role"]]
    context = {
        "teams": public_and_member_teams,
        "team_count": len(public_and_member_teams),
        "categories": MOCK_CATEGORIES,
        "active_page": "teams",
    }
    return render(request, "mockups/teams/browse.html", context)


def teams_create(request):
    """FOB-TEAMS-CREATE-1: Create a new team."""
    logger.info("Mockup: teams_create | user=%s", getattr(request.user, "username", "anonymous"))
    context = {
        "categories": MOCK_CATEGORIES,
        "errors": {},
        "active_page": "teams",
    }
    return render(request, "mockups/teams/create.html", context)


def teams_detail(request, team_id):
    """FOB-TEAMS-VIEW-1: View team detail, join, and leave.

    team_id=1: Usability — non-member, Auto-approve (Join button)
    team_id=2: UX — Maria is admin (Manage button)
    team_id=3: Front-End Guild — Maria is member (Leave button)
    team_id=4: Acme INC — Invite Only (no join, invite notice)
    """
    logger.info("Mockup: teams_detail | team_id=%s | user=%s", team_id, getattr(request.user, "username", "anonymous"))
    team = _MOCK_TEAMS_BY_ID.get(team_id, _MOCK_TEAMS_BY_ID[1])
    join_states = {
        None: "join",          # non-member
        "member": "leave",
        "admin": "manage",
        "pending": "pending",
    }
    join_state = join_states.get(team["maria_role"], "join")
    if team["join_policy"] == "Invite Only" and not team["maria_role"]:
        join_state = "invite_only"
    context = {
        "team": team,
        "join_state": join_state,
        "playbooks": MOCK_TEAM_PLAYBOOKS.get(team_id, []),
        "members": MOCK_TEAM_MEMBERS.get(team_id, [])[:5],
        "member_count": team["member_count"],
        "active_page": "teams",
    }
    return render(request, "mockups/teams/detail.html", context)


def teams_manage(request, team_id):
    """FOB-TEAMS-MANAGE-1: Admin management panel — members, join requests, playbooks, settings."""
    logger.info("Mockup: teams_manage | team_id=%s | user=%s", team_id, getattr(request.user, "username", "anonymous"))
    team = _MOCK_TEAMS_BY_ID.get(team_id, _MOCK_TEAMS_BY_ID[2])
    context = {
        "team": team,
        "members": MOCK_TEAM_MEMBERS.get(team_id, []),
        "join_requests": MOCK_JOIN_REQUESTS,
        "join_request_count": len(MOCK_JOIN_REQUESTS),
        "playbooks": MOCK_TEAM_PLAYBOOKS.get(team_id, []),
        "categories": MOCK_CATEGORIES,
        "active_page": "teams",
    }
    return render(request, "mockups/teams/manage.html", context)


# ---------------------------------------------------------------------------
# Global search (NAV-06) — mock data
# ---------------------------------------------------------------------------

SEARCH_ENTITY_META = [
    {
        "key": "playbooks",
        "label": "Playbooks",
        "label_singular": "Playbook",
        "icon": "fa-book-sparkles",
        "icon_class": "text-primary",
        "badge_class": "bg-primary",
    },
    {
        "key": "workflows",
        "label": "Workflows",
        "label_singular": "Workflow",
        "icon": "fa-diagram-project",
        "icon_class": "text-info",
        "badge_class": "bg-info",
    },
    {
        "key": "phases",
        "label": "Phases",
        "label_singular": "Phase",
        "icon": "fa-layer-group",
        "icon_class": "mm-search-icon-phase",
        "badge_class": "mm-search-badge-phase",
    },
    {
        "key": "activities",
        "label": "Activities",
        "label_singular": "Activity",
        "icon": "fa-list-check",
        "icon_class": "text-success",
        "badge_class": "bg-success",
    },
    {
        "key": "artifacts",
        "label": "Artifacts",
        "label_singular": "Artifact",
        "icon": "fa-file-lines",
        "icon_class": "text-warning",
        "badge_class": "bg-warning text-dark",
    },
    {
        "key": "skills",
        "label": "Skills",
        "label_singular": "Skill",
        "icon": "fa-wand-magic-sparkles",
        "icon_class": "mm-search-icon-skill",
        "badge_class": "mm-search-badge-skill",
    },
    {
        "key": "agents",
        "label": "Agents",
        "label_singular": "Agent",
        "icon": "fa-robot",
        "icon_class": "mm-search-icon-agent",
        "badge_class": "mm-search-badge-agent",
    },
    {
        "key": "rules",
        "label": "Rules",
        "label_singular": "Rule",
        "icon": "fa-gavel",
        "icon_class": "text-secondary",
        "badge_class": "bg-secondary",
    },
]

MOCK_SEARCH_ITEMS = [
    {
        "entity_key": "playbooks",
        "id": 1,
        "title": "React Frontend Development",
        "context": "Mike Chen · v1.2 · Development",
        "snippet": "Modern React patterns and component architecture for production frontends.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "playbooks",
        "id": 2,
        "title": "React Testing Patterns",
        "context": "Community · v1.0 · Released",
        "snippet": "Jest, React Testing Library, and component integration testing workflows.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "workflows",
        "id": 10,
        "title": "Component Development",
        "context": "React Frontend Development · 8 activities",
        "snippet": "Build and refine React components with state, props, and composition.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "workflows",
        "id": 11,
        "title": "Testing & Documentation",
        "context": "React Frontend Development · 6 activities",
        "snippet": "React component tests, storybook docs, and accessibility checks.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "workflows",
        "id": 12,
        "title": "State Management Setup",
        "context": "React Frontend Development · 4 activities",
        "snippet": "Redux Toolkit store wiring for React applications.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "phases",
        "id": 3,
        "title": "Construction",
        "context": "React Frontend Development",
        "snippet": "Implementation phase covering React build-out and integration.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "activities",
        "id": 20,
        "title": "Setup React Project",
        "context": "React Frontend Development › Component Development",
        "snippet": "Initialize Vite + React, configure ESLint, and scaffold the repo.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "activities",
        "id": 21,
        "title": "Create React Components",
        "context": "React Frontend Development › Component Development",
        "snippet": "Define presentational and container components with typed props.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "activities",
        "id": 22,
        "title": "Component Testing",
        "context": "React Frontend Development › Testing & Documentation",
        "snippet": "Write Jest tests for React components including axe-core checks.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "artifacts",
        "id": 30,
        "title": "Component Library Spec",
        "context": "React Frontend Development · Document",
        "snippet": "Catalog of React components, props, and usage examples.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "artifacts",
        "id": 31,
        "title": "Storybook Export",
        "context": "React Frontend Development · Template",
        "snippet": "Exported React story templates for design review.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "skills",
        "id": 40,
        "title": "React Form Component",
        "context": "GUI_FORM · React+Redux",
        "snippet": "Install deps, wire Redux store, validate on submit with React Hook Form.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "skills",
        "id": 41,
        "title": "React Router Setup",
        "context": "NAV_ROUTING · React+Router",
        "snippet": "Configure routes, loaders, and nested layouts in React Router v6.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "skills",
        "id": 42,
        "title": "React Query Data Fetch",
        "context": "API_FETCH · React+TanStack",
        "snippet": "Fetch and cache server state with TanStack Query in React apps.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "agents",
        "id": 50,
        "title": "Cautious Developer",
        "context": "React Frontend Development",
        "snippet": "Careful, test-driven React implementation with regression checks.",
        "detail_url_name": "mockup_search_results",
    },
    {
        "entity_key": "rules",
        "id": 60,
        "title": "do-react-testing",
        "context": "React Frontend Development · alwaysApply",
        "snippet": "Always add React Testing Library tests when changing components.",
        "detail_url_name": "mockup_search_results",
    },
]

_SEARCH_META_BY_KEY = {m["key"]: m for m in SEARCH_ENTITY_META}

_ENTITY_TESTID_SINGULAR = {
    "playbooks": "playbook",
    "workflows": "workflow",
    "phases": "phase",
    "activities": "activity",
    "artifacts": "artifact",
    "skills": "skill",
    "agents": "agent",
    "rules": "rule",
}


def _mock_search_matches(query: str):
    """Return items whose title, context, or snippet match query (case-insensitive)."""
    needle = (query or "").strip().lower()
    if not needle:
        return []
    matches = []
    for item in MOCK_SEARCH_ITEMS:
        haystack = " ".join(
            [item["title"], item.get("context", ""), item.get("snippet", "")]
        ).lower()
        if needle in haystack:
            enriched = dict(item)
            meta = _SEARCH_META_BY_KEY[item["entity_key"]]
            enriched.update(
                {
                    "type_label": meta["label_singular"],
                    "icon": meta["icon"],
                    "icon_class": meta["icon_class"],
                    "badge_class": meta["badge_class"],
                    "testid": (
                        f"global-search-result-"
                        f"{_ENTITY_TESTID_SINGULAR[item['entity_key']]}-{item['id']}"
                    ),
                }
            )
            matches.append(enriched)
    return matches


def _mock_search_grouped(query: str, type_filter: str):
    """Group matching items by entity type; honour optional type_filter."""
    matches = _mock_search_matches(query)
    grouped = {meta["key"]: [] for meta in SEARCH_ENTITY_META}
    for item in matches:
        grouped[item["entity_key"]].append(item)

    sections = []
    total = 0
    for meta in SEARCH_ENTITY_META:
        key = meta["key"]
        if type_filter and type_filter != key:
            continue
        items = grouped[key]
        if not items:
            continue
        total += len(items)
        sections.append(
            {
                "key": key,
                "label": meta["label"],
                "testid": f"global-search-{key}",
                "items": items,
                "count": len(items),
                "icon": meta["icon"],
                "icon_class": meta["icon_class"],
            }
        )
    return sections, total


def search_results(request):
    """FOB Search Results (NAV-06): grouped global search mockup.

    Query params:
      q     — search text (default demo: React when unset on first visit is handled in template)
      type  — entity type key (playbooks, workflows, …) or empty for all
    """
    query = (request.GET.get("q") or "").strip()
    type_filter = (request.GET.get("type") or "").strip()
    if type_filter and type_filter not in _SEARCH_META_BY_KEY:
        type_filter = ""

    logger.info(
        "Mockup: search_results | q=%r type=%r user=%s",
        query,
        type_filter or "all",
        getattr(request.user, "username", "anonymous"),
    )

    sections, total_count = _mock_search_grouped(query, type_filter)
    type_choices = [{"value": "", "label": "All types"}] + [
        {"value": m["key"], "label": m["label"]} for m in SEARCH_ENTITY_META
    ]

    context = {
        "query": query,
        "type_filter": type_filter,
        "type_choices": type_choices,
        "sections": sections,
        "total_count": total_count,
        "has_query": bool(query),
        "show_empty_state": bool(query) and total_count == 0,
        "show_no_query_prompt": not query,
        "entity_meta": SEARCH_ENTITY_META,
        "active_page": "search",
    }
    return render(request, "mockups/search/results.html", context)


def search_suggestions(request):
    """FOB Global Search suggestions dropdown mockup (navbar HTMX fragment)."""
    query = (request.GET.get("q") or "").strip()
    logger.info(
        "Mockup: search_suggestions | q=%r user=%s",
        query,
        getattr(request.user, "username", "anonymous"),
    )

    if not query:
        return render(
            request,
            "mockups/search/partials/suggestions.html",
            {"query": "", "sections": [], "total_count": 0},
        )

    matches = _mock_search_matches(query)
    grouped = {meta["key"]: [] for meta in SEARCH_ENTITY_META}
    for item in matches:
        grouped[item["entity_key"]].append(item)

    sections = []
    total = 0
    for meta in SEARCH_ENTITY_META:
        items = grouped[meta["key"]][:5]
        if not items:
            continue
        total += len(grouped[meta["key"]])
        sections.append(
            {
                "key": meta["key"],
                "label": meta["label"],
                "items": items,
                "count": len(grouped[meta["key"]]),
            }
        )

    return render(
        request,
        "mockups/search/partials/suggestions.html",
        {"query": query, "sections": sections, "total_count": total},
    )


# ---------------------------------------------------------------------------
# Copy Prompt mockup (Act 17)
# ---------------------------------------------------------------------------

MOCK_COPY_PROMPT_PLAYBOOK = {
    "name": "React Frontend Development",
    "version": "1.2",
    "status": "Released",
}

MOCK_COPY_PROMPT_WORKFLOW = {
    "name": "Component Development",
}

MOCK_COPY_PROMPT_ACTIVITY = {
    "id": 1,
    "name": "Setup component structure",
    "reference_label": "CD-01",
    "order": 1,
    "phase": "Planning",
    "updated_ago": "2 days",
    "guidance": (
        "## Overview\n\n"
        "Scaffold the component folder structure before implementation.\n\n"
        "## Steps\n\n"
        "1. Create `components/` directory\n"
        "2. Add index barrel export\n"
        "3. Document naming conventions\n"
    ),
}

MOCK_COPY_PROMPT_ACTIVITY_TEXT = (
    "Read the 'CD-01 Setup component structure' activity from playbook "
    "'React Frontend Development' (workflow 'Component Development'). "
    "Follow its guidance when assisting me.\n\n"
    "## Overview\n\n"
    "Scaffold the component folder structure before implementation.\n\n"
    "## Steps\n\n"
    "1. Create `components/` directory\n"
    "2. Add index barrel export\n"
    "3. Document naming conventions\n"
)

MOCK_COPY_PROMPT_ACTIVITIES = [
    {
        "id": 1,
        "name": "Setup component structure",
        "reference_label": "CD-01",
        "order": 1,
        "phase": "Planning",
        "copy_prompt_text": MOCK_COPY_PROMPT_ACTIVITY_TEXT,
    },
    {
        "id": 2,
        "name": "Implement component",
        "reference_label": "CD-02",
        "order": 2,
        "phase": "Execution",
        "copy_prompt_text": (
            "Read the 'CD-02 Implement component' activity from playbook "
            "'React Frontend Development' (workflow 'Component Development'). "
            "Follow its guidance when assisting me.\n\n"
            "(Mock body — implement the component per design spec.)\n"
        ),
    },
    {
        "id": 3,
        "name": "Component testing",
        "reference_label": "CD-03",
        "order": 3,
        "phase": "Execution",
        "copy_prompt_text": (
            "Read the 'CD-03 Component testing' activity from playbook "
            "'React Frontend Development' (workflow 'Component Development'). "
            "Follow its guidance when assisting me.\n\n"
            "(Mock body — add Jest tests for the component.)\n"
        ),
    },
]


def copy_prompt_index(request):
    """FOB-COPY-PROMPT mockup hub — links to VIEW and LIST exemplars."""
    logger.info(
        "Mockup: copy_prompt_index | user=%s",
        getattr(request.user, "username", "anonymous"),
    )
    return render(request, "mockups/copy-prompt/index.html")


def copy_prompt_activity_detail(request):
    """FOB-COPY-PROMPT-VIEW-1 mockup — activity detail with header Copy Prompt."""
    logger.info(
        "Mockup: copy_prompt_activity_detail | user=%s",
        getattr(request.user, "username", "anonymous"),
    )
    context = {
        "playbook": MOCK_COPY_PROMPT_PLAYBOOK,
        "workflow": MOCK_COPY_PROMPT_WORKFLOW,
        "activity": MOCK_COPY_PROMPT_ACTIVITY,
        "copy_prompt_text": MOCK_COPY_PROMPT_ACTIVITY_TEXT,
    }
    return render(request, "mockups/copy-prompt/activity_detail.html", context)


def copy_prompt_activity_list(request):
    """FOB-COPY-PROMPT-LIST-1 mockup — activities table with row Copy Prompt."""
    logger.info(
        "Mockup: copy_prompt_activity_list | user=%s",
        getattr(request.user, "username", "anonymous"),
    )
    context = {
        "playbook": MOCK_COPY_PROMPT_PLAYBOOK,
        "workflow": MOCK_COPY_PROMPT_WORKFLOW,
        "activities": MOCK_COPY_PROMPT_ACTIVITIES,
    }
    return render(request, "mockups/copy-prompt/activity_list.html", context)
