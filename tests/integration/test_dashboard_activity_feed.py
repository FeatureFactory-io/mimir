"""Integration tests for dashboard Recently Contributed activity feed (FOB-DASHBOARD-09..13)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import Activity, Playbook, Workflow

User = get_user_model()


def _create_playbook_with_activities(user, activity_specs):
    """Create playbook/workflow and activities; specs are (name, hours_ago)."""
    playbook = Playbook.objects.create(
        name="Feed Test Playbook",
        description="Test",
        category="development",
        author=user,
    )
    workflow = Workflow.objects.create(
        playbook=playbook,
        name="Feed Test Workflow",
        description="Test",
    )
    activities = []
    now = timezone.now()
    for order, (name, hours_ago) in enumerate(activity_specs, start=1):
        activity = Activity.objects.create(
            workflow=workflow,
            name=name,
            guidance="Test",
            order=order,
        )
        if hours_ago is not None:
            ts = now - timedelta(hours=hours_ago)
            Activity.objects.filter(pk=activity.pk).update(
                last_accessed_at=ts,
                updated_at=ts,
            )
        activities.append(activity)
    return playbook, activities


@pytest.mark.django_db
class TestDashboardActivityFeed:
    """Recently Contributed feed time-window filter and HTMX refresh."""

    def test_dashboard_shows_recently_used_section_title(self):
        client = Client()
        user = User.objects.create_user(username="maria", password="pass123")
        client.force_login(user)

        response = client.get(reverse("dashboard"))
        content = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="recently-used-section"' in content
        assert "Recently Contributed" in content
        assert "Recent Activity" not in content
        assert ">Recently Used<" not in content

    def test_dashboard_empty_state_shows_contribution_copy(self):
        """Empty feed shows contribution-themed helper copy on full dashboard load."""
        client = Client()
        user = User.objects.create_user(username="maria_empty", password="pass123")
        client.force_login(user)

        response = client.get(reverse("dashboard"))
        content = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="no-activities"' in content
        assert "No recent activity" in content
        assert (
            "Your contribution activity will appear here as you contribute to Mimir"
            in content
        )

    def test_dashboard_activities_empty_state_shows_contribution_copy(self):
        """HTMX feed refresh shows the same empty-state copy when window has no rows."""
        client = Client()
        user = User.objects.create_user(username="maria_empty_htmx", password="pass123")
        client.force_login(user)

        response = client.get(reverse("dashboard_activities"), {"hours": 24})
        content = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="no-activities"' in content
        assert (
            "Your contribution activity will appear here as you contribute to Mimir"
            in content
        )

    def test_dashboard_default_load_uses_24h_window(self):
        client = Client()
        user = User.objects.create_user(username="maria24", password="pass123")
        _create_playbook_with_activities(
            user,
            [
                ("Fresh Activity", 2),
                ("Stale Activity", 48),
            ],
        )
        client.force_login(user)

        response = client.get(reverse("dashboard"))
        content = response.content.decode("utf-8")

        assert "Fresh Activity" in content
        assert "Stale Activity" not in content

    def test_dashboard_activities_respects_hours_query(self):
        client = Client()
        user = User.objects.create_user(username="maria_hours", password="pass123")
        _create_playbook_with_activities(
            user,
            [
                ("Recent Half Hour", 0.5),
                ("Five Hours Ago", 5),
            ],
        )
        client.force_login(user)

        response = client.get(reverse("dashboard_activities"), {"hours": 1})
        content = response.content.decode("utf-8")

        assert response.status_code == 200
        assert "Recent Half Hour" in content
        assert "Five Hours Ago" not in content

    def test_activity_feed_dropdown_label_reflects_hours(self):
        client = Client()
        user = User.objects.create_user(username="maria_label", password="pass123")
        client.force_login(user)

        response = client.get(reverse("dashboard_activities"), {"hours": 1})
        content = response.content.decode("utf-8")

        assert 'data-testid="recently-used-hours-label"' in content
        assert "Last hour" in content

    def test_refresh_preserves_hours_param(self):
        client = Client()
        user = User.objects.create_user(username="maria_refresh", password="pass123")
        client.force_login(user)

        response = client.get(reverse("dashboard_activities"), {"hours": 1})
        content = response.content.decode("utf-8")

        assert 'data-testid="refresh-activities-button"' in content
        assert "/dashboard/activities/?hours=1" in content

    def test_recently_used_badge_shows_window_count(self):
        client = Client()
        user = User.objects.create_user(username="maria_badge", password="pass123")
        _create_playbook_with_activities(
            user,
            [
                ("In Window 1", 1),
                ("In Window 2", 2),
                ("In Window 3", 3),
                ("Outside 1", 72),
                ("Outside 2", 96),
            ],
        )
        client.force_login(user)

        response = client.get(reverse("dashboard"))
        content = response.content.decode("utf-8")

        assert 'data-testid="recently-used-window-count"' in content
        assert "3 in last 24h" in content
        assert "5 recent" not in content.lower()

    def test_dashboard_activities_log_story(self, caplog):
        import logging

        from tests.support.log_story import assert_log_story

        caplog.set_level(logging.INFO)
        client = Client()
        user = User.objects.create_user(username="maria_log", password="pass123")
        client.force_login(user)

        client.get(reverse("dashboard_activities"), {"hours": 24})

        assert_log_story(
            caplog,
            where="dashboard_activities",
            beats={
                "entry": ["hours="],
            },
        )
