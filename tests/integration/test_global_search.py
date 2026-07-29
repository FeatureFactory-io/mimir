import logging

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from methodology.models import Activity, Playbook, Skill, Workflow
from tests.support.log_story import assert_log_story


@pytest.mark.django_db
class TestGlobalSearchView:
    """Integration tests for NAV-06 Global search endpoint and navbar wiring."""

    def _create_sample_data(self, user: User):
        playbook = Playbook.objects.create(
            name="Component Development Playbook",
            description="Playbook for components",
            category="development",
            author=user,
        )
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Component Workflow",
            description="Workflow for components",
            order=1,
        )
        Activity.objects.create(
            workflow=workflow,
            name="Create Component",
            guidance="Do component work",
            order=1,
        )
        Skill.objects.create(
            playbook=playbook,
            title="React Component Skill",
            capability_domain="GUI",
            technology_stack="React",
            content="Build React components",
        )
        return playbook

    def test_global_search_page_shows_results_for_query(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search"), {"q": "Component"})
        assert response.status_code == 200
        html = response.content.decode("utf-8")

        assert "Component Development Playbook" in html
        assert "Component Workflow" in html
        assert "Create Component" in html
        assert 'data-testid="global-search-summary"' in html

    def test_global_search_type_filter_playbooks_only(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(
            reverse("global_search"), {"q": "Component", "type": "playbooks"}
        )
        assert response.status_code == 200
        html = response.content.decode("utf-8")

        assert "Component Development Playbook" in html
        assert 'data-testid="global-search-playbooks"' in html
        assert 'id="global-search-sections"' not in html
        assert "Component Workflow" not in html
        assert "Create Component" not in html

    def test_results_page_filter_bar_q_and_type_only(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)

        response = client.get(reverse("global_search"), {"q": "React"})
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-filters-form"' in html
        assert 'data-testid="global-search-query-input"' in html
        assert 'data-testid="global-search-type-filter"' in html
        assert 'data-testid="global-search-submit-button"' in html
        assert 'data-testid="filter-status"' not in html
        assert 'data-testid="filter-source"' not in html

    def test_results_page_accordion_first_section_expanded(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search"), {"q": "Component"})
        html = response.content.decode("utf-8")

        assert 'id="global-search-sections"' in html
        assert 'data-testid="global-search-section-toggle-playbooks"' in html
        assert 'id="collapse-playbooks"' in html
        assert 'class="accordion-collapse collapse show"' in html

    def test_results_page_single_type_no_accordion(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(
            reverse("global_search"), {"q": "React", "type": "skills"}
        )
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-skills"' in html
        assert 'id="global-search-sections"' not in html
        assert 'data-testid="global-search-playbooks"' not in html

    def test_results_page_highlight_in_html(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search"), {"q": "component"})
        html = response.content.decode("utf-8")

        assert '<mark class="mm-search-highlight">' in html
        assert "Component" in html

    def test_results_page_no_query_prompt(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)

        response = client.get(reverse("global_search"))
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-no-query-prompt"' in html
        assert 'data-testid="global-search-summary"' not in html

    def test_results_page_empty_state(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)

        response = client.get(reverse("global_search"), {"q": "zzzznomatch"})
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-empty-state"' in html
        assert "zzzznomatch" in html

    def test_result_link_navigates_to_detail(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        playbook = self._create_sample_data(user)

        response = client.get(reverse("global_search"), {"q": "Component"})
        html = response.content.decode("utf-8")
        detail_url = reverse("playbook_detail", kwargs={"pk": playbook.pk})
        assert detail_url in html

        detail_response = client.get(detail_url)
        assert detail_response.status_code == 200

    def test_global_search_log_story_happy(self, caplog):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        with caplog.at_level(logging.INFO):
            client.get(reverse("global_search"), {"q": "Component"})

        assert_log_story(
            caplog,
            where="Global search requested",
            beats={"entry": ["maria", "Component"]},
        )
        assert_log_story(
            caplog,
            where="Global search completed",
            beats={"exit": ["maria", "Component", "total matches"]},
        )

    def test_global_search_log_story_reject(self, caplog):
        service_logger = "methodology.services.global_search_service"
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        from methodology.services.global_search_service import GlobalSearchService

        with caplog.at_level(logging.INFO, logger=service_logger):
            GlobalSearchService().search(query="", user=user, filters=None)

        assert_log_story(
            caplog,
            where="GlobalSearchService.search",
            beats={"empty": ["empty query"]},
        )

    def test_navbar_contains_global_search_form_for_authenticated_user(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)

        response = client.get("/")
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-form"' in html
        assert 'data-testid="global-search-input"' in html
        assert 'name="q"' in html

    def test_navbar_does_not_show_global_search_for_anonymous_user(self):
        client = Client()
        response = client.get("/")
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-form"' not in html
        assert 'data-testid="global-search-input"' not in html

    def test_global_search_suggestions_returns_results_fragment(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search_suggestions"), {"q": "Component"})
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-suggestions"' in html
        assert 'data-testid="global-search-see-all-results"' in html
        assert "Development Playbook" in html
        assert '<mark class="mm-search-highlight">Component</mark>' in html

    def test_suggestions_highlight_query(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search_suggestions"), {"q": "react"})
        html = response.content.decode("utf-8")

        assert '<mark class="mm-search-highlight">' in html
        assert "React" in html

    def test_global_search_suggestions_requires_authentication(self):
        client = Client()
        response = client.get(reverse("global_search_suggestions"), {"q": "Component"})
        assert response.status_code in (302, 301)

    def test_global_search_suggestions_empty_query_returns_empty_fragment(self):
        client = Client()
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        client.force_login(user)
        self._create_sample_data(user)

        response = client.get(reverse("global_search_suggestions"), {"q": " "})
        html = response.content.decode("utf-8")

        assert 'data-testid="global-search-suggestions"' not in html
        assert "Component Development Playbook" not in html
