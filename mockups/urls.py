from django.urls import path
from . import views

urlpatterns = [
    # ── Use cases (public landing) ────────────────────────────────────────
    path("use-cases/", views.use_cases, name="mockup_use_cases"),
    # ── Auth flow ──────────────────────────────────────────────────────────
    path("auth/register/", views.auth_register, name="mockup_auth_register"),
    path("auth/login/", views.auth_login, name="mockup_auth_login"),
    # ── Profile ───────────────────────────────────────────────────────────
    path("profile/", views.profile_view, name="mockup_profile"),
    path("profile/edit/", views.profile_edit, name="mockup_profile_edit"),
    # ── PIPs ──────────────────────────────────────────────────────────────
    path("pips/", views.pip_list, name="mockup_pip_list"),
    path("pips/create/", views.pip_create, name="mockup_pip_create"),
    path("pips/<int:pip_id>/", views.pip_detail, name="mockup_pip_detail"),
    path("pips/<int:pip_id>/admin-review/", views.pip_admin_review, name="mockup_pip_admin_review"),
    # ── Teams ─────────────────────────────────────────────────────────────
    path("teams/", views.teams_browse, name="mockup_teams_browse"),
    path("teams/create/", views.teams_create, name="mockup_teams_create"),
    path("teams/<int:team_id>/", views.teams_detail, name="mockup_teams_detail"),
    path("teams/<int:team_id>/manage/", views.teams_manage, name="mockup_teams_manage"),
    # ── Global search (NAV-06 mockup) ───────────────────────────────────────
    path("search/", views.search_results, name="mockup_search_results"),
    path("search/suggestions/", views.search_suggestions, name="mockup_search_suggestions"),
    # ── Copy Prompt (Act 17 mockup) ─────────────────────────────────────────
    path("copy-prompt/", views.copy_prompt_index, name="mockup_copy_prompt_index"),
    path(
        "copy-prompt/activities/",
        views.copy_prompt_activity_list,
        name="mockup_copy_prompt_activity_list",
    ),
    path(
        "copy-prompt/activities/empty/",
        views.copy_prompt_activity_list_empty,
        name="mockup_copy_prompt_activity_list_empty",
    ),
    path(
        "copy-prompt/activities/1/",
        views.copy_prompt_activity_detail,
        name="mockup_copy_prompt_activity_detail",
    ),
    path(
        "copy-prompt/activities/1/guest/",
        views.copy_prompt_activity_detail_guest,
        name="mockup_copy_prompt_activity_detail_guest",
    ),
    path(
        "copy-prompt/activities/1/embed/",
        views.copy_prompt_activity_embed,
        name="mockup_copy_prompt_activity_embed",
    ),
    path(
        "copy-prompt/activities/1/error/",
        views.copy_prompt_activity_detail_error,
        name="mockup_copy_prompt_activity_detail_error",
    ),
]
