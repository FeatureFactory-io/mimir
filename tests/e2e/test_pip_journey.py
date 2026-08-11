"""E2E sanity + revert-to-draft flow: PIP list and detail (Act 9)."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from playwright.sync_api import Page

from accounts.models import mark_email_verified
from methodology.models import (
    Activity,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Workflow,
)
from methodology.services.pip_service import PIPService

User = get_user_model()


@pytest.fixture
def pip_e2e_user(db):
    u = User.objects.create_user(
        username="pip_e2e", password="pipE2Epw!", email="e2e@example.test"
    )
    mark_email_verified(u)
    return u


@pytest.fixture
def pip_withdraw_user(db):
    u = User.objects.create_user(
        username="pip_withdraw_e2e", password="wdE2Epw!", email="wd_e2e@example.test"
    )
    mark_email_verified(u)
    return u


@pytest.fixture
def submitted_pip_for_e2e(db, pip_withdraw_user):
    pb = Playbook.objects.create(
        name="E2E Revert PB",
        description="d" * 30,
        category="development",
        author=pip_withdraw_user,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Main", order=1)
    act = Activity.objects.create(workflow=wf, name="Step", guidance="g" * 20, order=1)
    pip = PIPService.create_draft_for_playbook(
        actor=pip_withdraw_user, playbook_id=pb.pk, title="E2E revert PIP", summary=""
    )
    PIPService.add_change(
        actor=pip_withdraw_user, pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="updated guidance", name="",
    )
    pip.status = ProcessImprovementProposal.STATUS_SUBMITTED
    pip.save(update_fields=["status"])
    return pip


@pytest.fixture
def reviewed_pip_for_e2e(db, pip_withdraw_user):
    pb = Playbook.objects.create(
        name="E2E Reviewed PB",
        description="d" * 30,
        category="development",
        author=pip_withdraw_user,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Main", order=1)
    act = Activity.objects.create(workflow=wf, name="Step", guidance="g" * 20, order=1)
    pip = PIPService.create_draft_for_playbook(
        actor=pip_withdraw_user, playbook_id=pb.pk, title="E2E reviewed PIP", summary=""
    )
    PIPService.add_change(
        actor=pip_withdraw_user, pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="guidance", name="",
    )
    pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    pip.save(update_fields=["status"])
    return pip


def _login_user(page: Page, live_server_url: str, username: str, password: str) -> None:
    page.goto(f"{live_server_url}{reverse('login')}")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_login_and_open_pip_list(page: Page, live_server_url: str, pip_e2e_user):
    login_url = f"{live_server_url}{reverse('login')}"

    page.goto(login_url)
    page.fill('input[name="username"]', "pip_e2e")
    page.fill('input[name="password"]', "pipE2Epw!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    page.goto(f"{live_server_url}{reverse('pip_list')}")
    page.wait_for_load_state("networkidle")
    txt = page.content()
    assert "PIPs" in txt or "pip-empty-state" in txt


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_pip_withdraw_button_visible_for_submitted_e2e(
    page: Page, live_server_url: str, pip_withdraw_user, submitted_pip_for_e2e
):
    """Submitted PIP detail shows both Withdraw-to-Draft and Cancel PIP buttons."""
    _login_user(page, live_server_url, "pip_withdraw_e2e", "wdE2Epw!")
    page.goto(f"{live_server_url}{reverse('pip_detail', kwargs={'pk': submitted_pip_for_e2e.pk})}")
    page.wait_for_load_state("networkidle")

    assert page.locator('[data-testid="pip-detail-revert-open"]').is_visible()
    assert page.locator('[data-testid="pip-detail-withdraw-open"]').is_visible()
    assert not page.locator('[data-testid="pip-detail-edit-draft"]').is_visible()

    page.locator('[data-testid="pip-detail-revert-open"]').click()
    page.wait_for_selector('[data-testid="pip-revert-modal"]', state="visible")
    assert "return to Draft" in page.locator('[data-testid="pip-revert-modal"]').inner_text().lower() or \
           "Return to Draft" in page.locator('[data-testid="pip-revert-modal"]').inner_text()

    page.locator('[data-testid="pip-detail-revert-confirm"]').click()
    page.wait_for_load_state("networkidle")

    badge = page.locator('[data-testid="pip-status-badge"]')
    assert badge.inner_text().strip().lower() == "draft"
    assert page.locator('[data-testid="pip-detail-edit-draft"]').is_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_pip_revert_and_withdraw_visible_for_reviewed_e2e(
    page: Page, live_server_url: str, pip_withdraw_user, reviewed_pip_for_e2e
):
    """Reviewed PIP detail shows Return to Draft and Cancel PIP (#162)."""
    _login_user(page, live_server_url, "pip_withdraw_e2e", "wdE2Epw!")
    page.goto(f"{live_server_url}{reverse('pip_detail', kwargs={'pk': reviewed_pip_for_e2e.pk})}")
    page.wait_for_load_state("networkidle")

    assert page.locator('[data-testid="pip-detail-revert-open"]').is_visible()
    assert page.locator('[data-testid="pip-detail-withdraw-open"]').is_visible()
