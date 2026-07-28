"""
Integration tests for anonymous guest public playbook browse.
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Phase,
    Playbook,
    Rule,
    Skill,
    Workflow,
)

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="owner", password="pass")


@pytest.fixture
def public_released(owner, db):
    return Playbook.objects.create(
        name="Public Released",
        description="Guest readable playbook for evaluation",
        category="development",
        author=owner,
        visibility="public",
        status="released",
        version=Decimal("1.0"),
    )


@pytest.fixture
def private_playbook(owner, db):
    return Playbook.objects.create(
        name="Private Playbook",
        description="Not for guests",
        category="development",
        author=owner,
        visibility="private",
        status="released",
        version=Decimal("1.0"),
    )


@pytest.fixture
def public_active(owner, db):
    return Playbook.objects.create(
        name="Public Active Legacy",
        description="Authenticated only for guests",
        category="development",
        author=owner,
        visibility="public",
        status="active",
        version=Decimal("1.0"),
    )


@pytest.fixture
def public_draft(owner, db):
    return Playbook.objects.create(
        name="Public Draft WIP",
        description="Draft public not for guests",
        category="development",
        author=owner,
        visibility="public",
        status="draft",
        version=Decimal("0.1"),
    )


@pytest.fixture
def workflow(public_released, db):
    return Workflow.objects.create(
        playbook=public_released,
        name="Guest Workflow",
        description="Workflow",
        order=1,
    )


@pytest.fixture
def phase(public_released, db):
    return Phase.objects.create(
        playbook=public_released,
        name="Guest Phase",
        description="Phase",
        order=1,
    )


@pytest.fixture
def activity(workflow, phase, db):
    return Activity.objects.create(
        workflow=workflow,
        phase=phase,
        name="Guest Activity",
        guidance="## Guest\nInitial guidance.",
        order=1,
    )


@pytest.fixture
def artifact(public_released, activity, db):
    return Artifact.objects.create(
        playbook=public_released,
        name="Guest Artifact",
        description="Artifact",
        type="Document",
        produced_by=activity,
        is_required=True,
    )


@pytest.fixture
def skill(public_released, db):
    return Skill.objects.create(
        playbook=public_released,
        title="Guest Skill",
        capability_domain="TEST",
        technology_stack="Django",
        content="## Skill",
    )


@pytest.fixture
def agent(public_released, db):
    return Agent.objects.create(
        playbook=public_released,
        name="Guest Agent",
        description="Agent persona",
    )


@pytest.fixture
def rule(public_released, db):
    return Rule.objects.create(
        playbook=public_released,
        title="Guest Rule",
        slug="guest-rule",
        content="Always apply for guests",
        always_apply=True,
    )


@pytest.fixture
def private_workflow(private_playbook, db):
    return Workflow.objects.create(
        playbook=private_playbook,
        name="Private Workflow",
        description="Hidden",
        order=1,
    )


@pytest.mark.django_db
class TestGuestLandingAndList:
    def test_landing_explore_cta(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b'data-testid="landing-cta-explore-playbooks"' in response.content

    def test_anonymous_playbooks_list_shows_released_public(
        self, client, public_released, public_active, private_playbook
    ):
        response = client.get(reverse("playbook_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert f'public-playbook-card-{public_released.pk}'.encode() in response.content
        assert f'public-playbook-card-{public_active.pk}'.encode() not in response.content
        assert f'public-playbook-card-{private_playbook.pk}'.encode() not in response.content
        assert b"Create New Playbook" not in response.content


@pytest.mark.django_db
class TestGuestPlaybookDetail:
    def test_public_released_detail_read_only(self, client, public_released):
        response = client.get(
            reverse("playbook_detail", kwargs={"pk": public_released.pk})
        )
        assert response.status_code == 200
        assert b'data-testid="playbook-detail"' in response.content
        assert b'data-testid="delete-button"' not in response.content

    def test_private_playbook_404(self, client, private_playbook):
        response = client.get(
            reverse("playbook_detail", kwargs={"pk": private_playbook.pk})
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestGuestLoginGates:
    def test_create_redirects_to_login(self, client):
        response = client.get(reverse("playbook_create"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_dashboard_redirects_to_login(self, client):
        response = client.get(reverse("dashboard"))
        assert response.status_code == 302

    def test_export_redirects_to_login(self, client, public_released):
        response = client.get(
            reverse("playbook_export", kwargs={"pk": public_released.pk})
        )
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_release_post_redirects_to_login(self, client, public_released):
        response = client.post(
            reverse("playbook_release", kwargs={"pk": public_released.pk})
        )
        assert response.status_code == 302
        assert "/login/" in response.url


@pytest.mark.django_db
class TestGuestNavbar:
    PRIMARY_NAV_TESTIDS = (
        b'data-testid="nav-dashboard"',
        b'data-testid="nav-playbooks"',
        b'data-testid="nav-workflows"',
        b'data-testid="nav-phases"',
        b'data-testid="nav-activities"',
        b'data-testid="nav-artifacts"',
        b'data-testid="nav-agents"',
        b'data-testid="nav-skills"',
        b'data-testid="nav-rules"',
        b'data-testid="nav-teams"',
        b'data-testid="nav-pips"',
    )

    def test_guest_nav_shows_full_primary_nav_on_playbook_list(self, client, public_released):
        response = client.get(reverse("playbook_list"))
        assert response.status_code == 200
        for testid in self.PRIMARY_NAV_TESTIDS:
            assert testid in response.content

    def test_guest_nav_shows_full_primary_nav_on_landing(self, client):
        response = client.get("/")
        assert response.status_code == 200
        for testid in self.PRIMARY_NAV_TESTIDS:
            assert testid in response.content

    def test_guest_nav_hides_authenticated_right_side_widgets(self, client):
        response = client.get(reverse("playbook_list"))
        assert response.status_code == 200
        assert b'data-testid="global-search-input"' not in response.content
        assert b'data-testid="notification-bell"' not in response.content
        assert b'data-testid="user-display"' not in response.content
        assert b'data-testid="register-link"' in response.content
        assert b'data-testid="login-link"' in response.content


@pytest.mark.django_db
class TestGuestQuickStats:
    def test_quick_stat_links_return_200(
        self,
        client,
        public_released,
        workflow,
        phase,
        activity,
        artifact,
        skill,
        agent,
        rule,
    ):
        detail = client.get(
            reverse("playbook_detail", kwargs={"pk": public_released.pk})
        )
        assert detail.status_code == 200
        for testid in (
            b'data-testid="stat-workflows-link"',
            b'data-testid="stat-phases-link"',
            b'data-testid="stat-activities-link"',
            b'data-testid="stat-artifacts-link"',
            b'data-testid="stat-agents-link"',
            b'data-testid="stat-skills-link"',
            b'data-testid="stat-rules-link"',
        ):
            assert testid in detail.content

        scoped_urls = [
            reverse("workflow_list", kwargs={"playbook_pk": public_released.pk}),
            reverse(
                "phase_list_global",
            )
            + f"?playbook={public_released.pk}",
            reverse(
                "activity_list_for_playbook", kwargs={"playbook_pk": public_released.pk}
            ),
            reverse("artifact_list", kwargs={"playbook_id": public_released.pk}),
            reverse(
                "agent_list_for_playbook", kwargs={"playbook_pk": public_released.pk}
            ),
            reverse(
                "skill_list_playbook", kwargs={"playbook_pk": public_released.pk}
            ),
            reverse(
                "rule_list_playbook", kwargs={"playbook_pk": public_released.pk}
            ),
        ]
        for url in scoped_urls:
            response = client.get(url)
            assert response.status_code == 200, url
            assert b'data-testid="guest-auth-banner"' in response.content


@pytest.mark.django_db
class TestGuestScopedLists:
    def test_workflow_list(self, client, public_released, workflow):
        url = reverse("workflow_list", kwargs={"playbook_pk": public_released.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Workflow" in response.content
        assert b'data-testid="create-workflow-button"' not in response.content

    def test_activity_list_for_playbook(self, client, public_released, activity):
        url = reverse(
            "activity_list_for_playbook", kwargs={"playbook_pk": public_released.pk}
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Activity" in response.content

    def test_activity_list_per_workflow(
        self, client, public_released, workflow, activity
    ):
        url = reverse(
            "activity_list",
            kwargs={"playbook_pk": public_released.pk, "workflow_pk": workflow.pk},
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Activity" in response.content
        assert b'data-testid="create-activity-btn"' not in response.content

    def test_artifact_list(self, client, public_released, artifact):
        url = reverse("artifact_list", kwargs={"playbook_id": public_released.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Artifact" in response.content

    def test_agent_list_for_playbook(self, client, public_released, agent):
        url = reverse(
            "agent_list_for_playbook", kwargs={"playbook_pk": public_released.pk}
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Agent" in response.content
        assert b"Create Agent" not in response.content

    def test_skill_list(self, client, public_released, skill):
        url = reverse("skill_list_playbook", kwargs={"playbook_pk": public_released.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Skill" in response.content

    def test_rule_list(self, client, public_released, rule):
        url = reverse("rule_list_playbook", kwargs={"playbook_pk": public_released.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Rule" in response.content

    def test_phase_list(self, client, public_released, phase):
        url = reverse("phase_list", kwargs={"playbook_pk": public_released.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guest Phase" in response.content

    def test_private_scoped_list_404(self, client, private_playbook):
        url = reverse("workflow_list", kwargs={"playbook_pk": private_playbook.pk})
        assert client.get(url).status_code == 404


@pytest.mark.django_db
class TestGuestDrillDown:
    def test_workflow_then_activity_detail(
        self, client, public_released, workflow, activity
    ):
        wf_url = reverse(
            "workflow_detail",
            kwargs={"playbook_pk": public_released.pk, "pk": workflow.pk},
        )
        wf_resp = client.get(wf_url)
        assert wf_resp.status_code == 200
        assert b'data-testid="workflow-detail-page"' in wf_resp.content

        act_url = reverse(
            "activity_detail",
            kwargs={
                "playbook_pk": public_released.pk,
                "workflow_pk": workflow.pk,
                "activity_pk": activity.pk,
            },
        )
        act_resp = client.get(act_url)
        assert act_resp.status_code == 200
        assert b"Guest Activity" in act_resp.content


@pytest.mark.django_db
class TestGuestGlobalEntityLists:
    def test_global_workflows_list(self, client, public_released, workflow, private_workflow):
        response = client.get(reverse("workflow_global_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Workflow" in response.content
        assert b"Private Workflow" not in response.content

    def test_global_activities_list(
        self, client, public_released, activity, public_draft, private_playbook
    ):
        response = client.get(reverse("activity_global_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Activity" in response.content

    def test_global_artifacts_list(self, client, artifact):
        response = client.get(reverse("artifact_list_global"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Artifact" in response.content

    def test_global_skills_list(self, client, skill):
        response = client.get(reverse("skill_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Skill" in response.content

    def test_global_agents_list(self, client, agent):
        response = client.get(reverse("agent_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Agent" in response.content

    def test_global_rules_list(self, client, rule):
        response = client.get(reverse("rule_list"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Rule" in response.content

    def test_global_phases_list(self, client, phase):
        response = client.get(reverse("phase_list_global"))
        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b"Guest Phase" in response.content


@pytest.mark.django_db
class TestGuestCanViewModel:
    def test_anonymous_released_public(self, public_released):
        assert public_released.can_view(AnonymousUser()) is True

    def test_anonymous_active_public_denied(self, public_active):
        assert public_active.can_view(AnonymousUser()) is False
