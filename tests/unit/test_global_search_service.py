import logging

import pytest
from django.contrib.auth.models import User

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
from methodology.services.global_search_service import (
    SEARCH_ENTITY_ORDER,
    GlobalSearchService,
)


@pytest.mark.django_db
class TestGlobalSearchService:
    """Unit tests for GlobalSearchService search behavior."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        self.other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="SecurePass123",
        )
        self.service = GlobalSearchService()

    def _create_full_fixture(self, author=None, name_prefix="Alpha"):
        author = author or self.user
        playbook = Playbook.objects.create(
            name=f"{name_prefix} Development Playbook",
            description=f"Playbook for {name_prefix} components",
            category="development",
            author=author,
        )
        workflow = Workflow.objects.create(
            playbook=playbook,
            name=f"{name_prefix} Workflow",
            description=f"Workflow for {name_prefix}",
            order=1,
        )
        activity = Activity.objects.create(
            workflow=workflow,
            name=f"Create {name_prefix}",
            guidance=f"Do {name_prefix} component work",
            order=1,
        )
        phase = Phase.objects.create(
            playbook=playbook,
            name=f"{name_prefix} Phase",
            description=f"Phase for {name_prefix}",
            order=1,
        )
        artifact = Artifact.objects.create(
            playbook=playbook,
            produced_by=activity,
            name=f"{name_prefix} Artifact",
            description=f"Artifact for {name_prefix}",
        )
        skill = Skill.objects.create(
            playbook=playbook,
            title=f"{name_prefix} Skill",
            capability_domain=f"{name_prefix}Domain",
            technology_stack="Django",
            content=f"Skill content about {name_prefix}",
        )
        agent = Agent.objects.create(
            playbook=playbook,
            name=f"{name_prefix} Agent",
            description=f"Agent for {name_prefix}",
        )
        rule = Rule.objects.create(
            playbook=playbook,
            title=f"{name_prefix} Rule",
            slug=f"{name_prefix.lower()}-rule",
            content=f"Rule content about {name_prefix}",
        )
        return {
            "playbook": playbook,
            "workflow": workflow,
            "activity": activity,
            "phase": phase,
            "artifact": artifact,
            "skill": skill,
            "agent": agent,
            "rule": rule,
        }

    def test_search_returns_all_entity_types_for_query(self):
        self._create_full_fixture(name_prefix="Alpha")

        results = self.service.search(query="Alpha", user=self.user, filters=None)

        for key in SEARCH_ENTITY_ORDER:
            assert key in results
            assert results[key], f"Expected matches in {key}"

    def test_search_with_no_matches_returns_empty_lists(self):
        results = self.service.search(query="NonExistingQuery", user=self.user, filters=None)

        for key in SEARCH_ENTITY_ORDER:
            assert results[key] == []

    def test_search_with_type_filter_limits_entity_lists(self):
        self._create_full_fixture(name_prefix="Alpha")

        results = self.service.search(
            query="Alpha", user=self.user, filters={"type": "playbooks"}
        )

        assert results["playbooks"]
        assert results["workflows"] == []
        assert results["activities"] == []
        assert results["phases"] == []

    def test_search_includes_public_playbook_not_owned(self):
        Playbook.objects.create(
            name="Public Shared Playbook",
            description="Visible to everyone",
            category="development",
            author=self.other,
            visibility="public",
            status="released",
        )

        results = self.service.search(query="Public Shared", user=self.user, filters=None)

        assert len(results["playbooks"]) == 1
        assert results["playbooks"][0].author_id == self.other.id

    def test_search_excludes_other_authors_draft(self):
        Playbook.objects.create(
            name="Secret Draft Playbook",
            description="Should not appear",
            category="development",
            author=self.other,
            visibility="public",
            status="draft",
        )

        results = self.service.search(query="Secret Draft", user=self.user, filters=None)

        assert results["playbooks"] == []

    def test_build_sections_includes_context_and_snippet(self):
        data = self._create_full_fixture(name_prefix="Alpha")
        results = self.service.search(query="Alpha", user=self.user, filters=None)
        sections, total = self.service.build_sections("Alpha", results, type_filter="")

        activity_section = next(s for s in sections if s["key"] == "activities")
        row = activity_section["items"][0]
        assert "Development Playbook" in row["context_html"]
        assert "Workflow" in row["context_html"]
        assert "Alpha" in row["snippet_html"]
        assert total >= 8

    def test_build_sections_omits_empty_entity_types(self):
        Playbook.objects.create(
            name="Lonely Playbook",
            description="Only playbook",
            category="development",
            author=self.user,
        )
        results = self.service.search(query="Lonely", user=self.user, filters=None)
        sections, total = self.service.build_sections("Lonely", results, type_filter="")

        assert len(sections) == 1
        assert sections[0]["key"] == "playbooks"
        assert total == 1

    def test_search_empty_query_log_story(self, caplog):
        with caplog.at_level(logging.INFO, logger="methodology.services.global_search_service"):
            results = self.service.search(query="", user=self.user, filters=None)

        assert results == {key: [] for key in SEARCH_ENTITY_ORDER}
        assert any("empty query" in r.getMessage() for r in caplog.records)

    def test_search_happy_path_log_story(self, caplog):
        self._create_full_fixture(name_prefix="Alpha")
        with caplog.at_level(logging.INFO, logger="methodology.services.global_search_service"):
            self.service.search(query="Alpha", user=self.user, filters=None)

        messages = [r.getMessage() for r in caplog.records]
        assert any("GlobalSearchService.search started" in m for m in messages)
        assert any("GlobalSearchService.search finished" in m for m in messages)
