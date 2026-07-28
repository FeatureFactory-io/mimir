"""Integration tests for landing page hero primary CTA (FOB-LANDING-CTA)."""

import re

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def _extract_testid_block(html: str, testid: str) -> str:
    pattern = rf'<a[^>]*data-testid="{re.escape(testid)}"[^>]*>.*?</a>'
    match = re.search(pattern, html, flags=re.DOTALL)
    assert match, f'Expected element with data-testid="{testid}"'
    return match.group(0)


@pytest.mark.django_db
class TestLandingHeroCta:
    def test_guest_landing_shows_register_with_user_plus_icon(self, client):
        response = client.get("/")

        assert response.status_code == 200
        body = response.content.decode()
        register_cta = _extract_testid_block(body, "landing-cta-register")
        assert "fa-user-plus" in register_cta
        assert "btn-success" in register_cta
        assert 'data-testid="landing-cta-connect-mcp"' not in body
        assert 'data-testid="landing-cta-connect"' not in body

    def test_authenticated_landing_shows_connect_mcp_primary_button(self, client):
        user = User.objects.create_user(username="maria", password="pass")
        client.force_login(user)
        response = client.get("/")

        assert response.status_code == 200
        body = response.content.decode()
        connect_cta = _extract_testid_block(body, "landing-cta-connect-mcp")
        assert "fa-plug" in connect_cta
        assert "btn-primary" in connect_cta
        assert 'data-testid="landing-cta-register"' not in body
        assert 'data-testid="landing-cta-connect"' not in body

    def test_connect_mcp_button_links_to_mcp_section(self, client):
        user = User.objects.create_user(username="maria2", password="pass")
        client.force_login(user)
        response = client.get("/")

        body = response.content.decode()
        connect_cta = _extract_testid_block(body, "landing-cta-connect-mcp")
        assert 'href="#mcp-config"' in connect_cta
        assert 'data-testid="landing-mcp-connect"' in body
        assert 'id="mcp-config"' in body
