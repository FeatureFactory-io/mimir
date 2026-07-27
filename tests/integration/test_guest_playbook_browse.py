"""
Integration tests for anonymous guest public playbook browse.
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.urls import reverse

from methodology.models import Playbook, Workflow

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
def workflow(public_released, db):
    return Workflow.objects.create(
        playbook=public_released,
        name="Guest Workflow",
        description="Workflow",
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


@pytest.mark.django_db
class TestGuestGlobalWorkflowsList:
    def test_global_workflows_list(self, client, public_released, workflow):
        response = client.get(reverse("workflow_global_list"))
        assert response.status_code == 200
        assert b"Guest Workflow" in response.content


@pytest.mark.django_db
class TestGuestCanViewModel:
    def test_anonymous_released_public(self, public_released):
        assert public_released.can_view(AnonymousUser()) is True

    def test_anonymous_active_public_denied(self, public_active):
        assert public_active.can_view(AnonymousUser()) is False
