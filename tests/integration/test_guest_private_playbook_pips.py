"""Guest access to PIPs on private playbooks must be denied end-to-end."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from methodology.models import Playbook, ProcessImprovementProposal

User = get_user_model()

PRIVATE_PIP_TITLE = "Secret private playbook PIP title"


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="pip_owner", password="pass")


@pytest.fixture
def private_released_playbook(owner, db):
    return Playbook.objects.create(
        name="Private Released Playbook",
        description="Must not leak PIPs to guests",
        category="development",
        author=owner,
        visibility="private",
        status="released",
        version=Decimal("1.0"),
    )


@pytest.fixture
def private_playbook_pip(owner, private_released_playbook, db):
    return ProcessImprovementProposal.objects.create(
        playbook=private_released_playbook,
        title=PRIVATE_PIP_TITLE,
        summary="Submitted change on a private playbook",
        status=ProcessImprovementProposal.STATUS_SUBMITTED,
        created_by=owner,
    )


@pytest.mark.django_db
class TestGuestCannotSeePrivatePlaybookPips:
    """Guests must not read PIPs tied to private playbooks via any HTTP surface."""

    def test_guest_pip_list_redirects_to_login(self, client, private_playbook_pip):
        response = client.get(reverse("pip_list"))

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_guest_pip_list_filtered_by_private_playbook_redirects_to_login(
        self, client, private_released_playbook, private_playbook_pip
    ):
        response = client.get(
            reverse("pip_list"),
            {"playbook": private_released_playbook.pk},
        )

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_guest_pip_detail_redirects_to_login(self, client, private_playbook_pip):
        response = client.get(
            reverse("pip_detail", kwargs={"pk": private_playbook_pip.pk})
        )

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_guest_private_playbook_detail_is_404_without_pip_leak(
        self, client, private_released_playbook, private_playbook_pip
    ):
        response = client.get(
            reverse("playbook_detail", kwargs={"pk": private_released_playbook.pk})
        )

        assert response.status_code == 404
        body = response.content.decode()
        assert PRIVATE_PIP_TITLE not in body
        assert f"PIP&nbsp;#{private_playbook_pip.pk}" not in body
        assert f'data-pip-id="{private_playbook_pip.pk}"' not in body

    def test_guest_api_pip_list_is_not_authenticated(
        self, client, private_playbook_pip
    ):
        response = client.get("/api/pips/")

        assert response.status_code in (401, 403)

    def test_guest_api_pip_detail_is_not_authenticated(
        self, client, private_playbook_pip
    ):
        response = client.get(f"/api/pips/{private_playbook_pip.pk}/")

        assert response.status_code in (401, 403)
