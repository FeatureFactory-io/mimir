"""Integration tests for the consent-gated Mimir product analytics contract."""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

User = get_user_model()

_LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
_MEASUREMENT_ID = "G-5LC9BFJRK8"


def test_guest_landing_with_analytics_contract_is_consent_gated(client):
    response = client.get("/")
    body = response.content.decode()

    assert response.status_code == 200
    assert f'data-analytics-measurement-id="{_MEASUREMENT_ID}"' in body
    assert 'data-analytics-enabled="true"' in body
    assert "data-analytics-consent" in body
    assert "data-analytics-settings" in body
    assert "js/product_analytics.js" in body
    assert "googletagmanager.com/gtag/js" not in body


@pytest.mark.django_db
def test_authenticated_page_with_analytics_contract_is_disabled(client):
    user = User.objects.create_user(username="analytics-user", password="pass")
    client.force_login(user)

    body = client.get("/").content.decode()

    assert 'data-analytics-enabled="true"' not in body
    assert "data-analytics-settings" not in body


def test_register_form_with_analytics_contract_marks_start_without_field_values(client):
    body = client.get(reverse("register")).content.decode()

    assert 'data-analytics-registration="account"' in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND=_LOCMEM)
def test_register_with_success_marks_only_server_confirmed_signup(client):
    response = client.post(
        reverse("register"),
        data={
            "first_name": "Analytics",
            "last_name": "Proof",
            "username": "analyticsproof",
            "email": "analyticsproof@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "accepted_tos": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert b"analytics-sign-up" in response.content


def test_product_analytics_source_with_privacy_contract_never_reads_form_values():
    source = Path("static/js/product_analytics.js").read_text(encoding="utf-8")

    assert "FormData" not in source
    assert "email" not in source.lower()
    assert "pageUrl.search" not in source
    assert "ga-disable-" in source
    assert 'analytics_storage: "denied"' in source
