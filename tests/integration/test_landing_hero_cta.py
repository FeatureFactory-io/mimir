"""Integration tests for landing page hero primary CTA (FOB-LANDING-CTA)."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestLandingHeroCta:
    def test_guest_landing_shows_register_with_user_plus_icon(self, client):
        response = client.get("/")

        assert response.status_code == 200
        body = response.content.decode()
        assert 'data-testid="landing-cta-register"' in body
        assert "fa-user-plus" in body
        assert 'data-testid="landing-cta-connect-mcp"' not in body

    def test_authenticated_landing_shows_connect_mcp_primary_button(self, client):
        user = User.objects.create_user(username="maria", password="pass")
        client.force_login(user)
        response = client.get("/")

        assert response.status_code == 200
        body = response.content.decode()
        assert 'data-testid="landing-cta-connect-mcp"' in body
        assert "fa-plug" in body
        assert "btn-primary" in body
        assert 'data-testid="landing-cta-register"' not in body

    def test_connect_mcp_button_links_to_mcp_section(self, client):
        user = User.objects.create_user(username="maria2", password="pass")
        client.force_login(user)
        response = client.get("/")

        body = response.content.decode()
        assert 'href="#mcp-config"' in body
        assert 'data-testid="landing-mcp-connect"' in body
        assert 'id="mcp-config"' in body
