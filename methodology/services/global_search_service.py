"""Service for NAV-06 global search across all playbook entity types."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils.html import strip_tags

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
from methodology.services.playbook_service import PlaybookService
from methodology.utils.markdown_renderer import render_markdown
from methodology.utils.search_highlight import highlight_search_term

logger = logging.getLogger(__name__)

SEARCH_ENTITY_ORDER: tuple[str, ...] = (
    "playbooks",
    "workflows",
    "phases",
    "activities",
    "artifacts",
    "skills",
    "agents",
    "rules",
)

SEARCH_ENTITY_META: tuple[Dict[str, str], ...] = (
    {"key": "playbooks", "label": "Playbooks", "label_singular": "Playbook", "icon": "fa-book-sparkles"},
    {"key": "workflows", "label": "Workflows", "label_singular": "Workflow", "icon": "fa-diagram-project"},
    {"key": "phases", "label": "Phases", "label_singular": "Phase", "icon": "fa-bars-progress"},
    {"key": "activities", "label": "Activities", "label_singular": "Activity", "icon": "fa-list-check"},
    {"key": "artifacts", "label": "Artifacts", "label_singular": "Artifact", "icon": "fa-gift"},
    {"key": "skills", "label": "Skills", "label_singular": "Skill", "icon": "fa-hand-holding-magic"},
    {"key": "agents", "label": "Agents", "label_singular": "Agent", "icon": "fa-brain-circuit"},
    {"key": "rules", "label": "Rules", "label_singular": "Rule", "icon": "fa-scale-balanced"},
)

ENTITY_TESTID_SINGULAR = {
    "playbooks": "playbook",
    "workflows": "workflow",
    "phases": "phase",
    "activities": "activity",
    "artifacts": "artifact",
    "skills": "skill",
    "agents": "agent",
    "rules": "rule",
}

SNIPPET_WORD_LIMIT = 20


class SearchResultRow(TypedDict):
    testid: str
    title: str
    title_html: str
    context_html: str
    snippet_html: str
    type_label: str
    icon: str
    url: str


class SearchSection(TypedDict):
    key: str
    label: str
    testid: str
    icon: str
    count: int
    items: List[SearchResultRow]


def _empty_results() -> Dict[str, List[Any]]:
    return {key: [] for key in SEARCH_ENTITY_ORDER}


def _truncate_snippet(text: str, word_limit: int = SNIPPET_WORD_LIMIT) -> str:
    words = (text or "").split()
    if len(words) <= word_limit:
        return " ".join(words)
    return " ".join(words[:word_limit]) + "…"


def _plain_text(value: str) -> str:
    if not value:
        return ""
    if any(token in value for token in ("##", "**", "`", "\n- ")):
        return strip_tags(render_markdown(value))
    return value


class GlobalSearchService:
    """Search methodology entities visible to the requesting user."""

    def search(
        self,
        query: str,
        user,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Any]]:
        """Search across all registered entity types.

        :param query: Free-text query.
        :param user: Authenticated Django user.
        :param filters: Optional ``type`` key to limit entity bucket.
        :return: Dict keyed by entity type with model instance lists.
        """
        filters = filters or {}
        normalized_query = (query or "").strip()

        if not normalized_query:
            logger.info(
                "GlobalSearchService.search called with empty query by user=%s",
                getattr(user, "username", "unknown"),
            )
            return _empty_results()

        logger.info(
            "GlobalSearchService.search started for user=%s, query='%s', filters=%s",
            user.username,
            normalized_query,
            filters,
        )

        raw = {
            "playbooks": list(self._search_playbooks(normalized_query, user)),
            "workflows": list(self._search_workflows(normalized_query, user)),
            "phases": list(self._search_phases(normalized_query, user)),
            "activities": list(self._search_activities(normalized_query, user)),
            "artifacts": list(self._search_artifacts(normalized_query, user)),
            "skills": list(self._search_skills(normalized_query, user)),
            "agents": list(self._search_agents(normalized_query, user)),
            "rules": list(self._search_rules(normalized_query, user)),
        }
        results = self._apply_type_filter(raw, filters.get("type"))

        logger.info(
            "GlobalSearchService.search finished for user=%s, query='%s' with "
            "%d playbooks, %d workflows, %d phases, %d activities, "
            "%d artifacts, %d skills, %d agents, %d rules",
            user.username,
            normalized_query,
            len(results["playbooks"]),
            len(results["workflows"]),
            len(results["phases"]),
            len(results["activities"]),
            len(results["artifacts"]),
            len(results["skills"]),
            len(results["agents"]),
            len(results["rules"]),
        )
        return results

    def build_sections(
        self,
        query: str,
        results: Dict[str, List[Any]],
        type_filter: str = "",
    ) -> tuple[List[SearchSection], int]:
        """Group raw search hits into UI sections with highlighted rows.

        :param query: Active search query for highlighting.
        :param results: Output of :meth:`search`.
        :param type_filter: Optional single entity type key.
        :return: Tuple of section dicts and total match count.
        """
        sections: List[SearchSection] = []
        total = 0
        meta_by_key = {m["key"]: m for m in SEARCH_ENTITY_META}

        for key in SEARCH_ENTITY_ORDER:
            if type_filter and type_filter != key:
                continue
            items_raw = results.get(key) or []
            if not items_raw:
                continue
            meta = meta_by_key[key]
            rows = [self._serialize_result(key, instance, query) for instance in items_raw]
            total += len(rows)
            sections.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "testid": f"global-search-{key}",
                    "icon": meta["icon"],
                    "count": len(rows),
                    "items": rows,
                }
            )
        return sections, total

    def _accessible_playbook_ids(self, user) -> set[int]:
        return PlaybookService.get_accessible_playbook_ids(user)

    def _apply_type_filter(
        self,
        results: Dict[str, List[Any]],
        type_filter: Optional[str],
    ) -> Dict[str, List[Any]]:
        if not type_filter or type_filter not in SEARCH_ENTITY_ORDER:
            return results
        return {key: (results[key] if key == type_filter else []) for key in SEARCH_ENTITY_ORDER}

    def _search_playbooks(self, query: str, user) -> QuerySet[Playbook]:
        ids = self._accessible_playbook_ids(user)
        return (
            Playbook.objects.filter(id__in=ids)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("author")
            .order_by("-updated_at")
        )

    def _search_workflows(self, query: str, user) -> QuerySet[Workflow]:
        ids = self._accessible_playbook_ids(user)
        return (
            Workflow.objects.filter(playbook_id__in=ids)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("playbook")
            .order_by("playbook__name", "order")
        )

    def _search_phases(self, query: str, user) -> QuerySet[Phase]:
        ids = self._accessible_playbook_ids(user)
        return (
            Phase.objects.filter(playbook_id__in=ids)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("playbook")
            .order_by("playbook__name", "order")
        )

    def _search_activities(self, query: str, user) -> QuerySet[Activity]:
        ids = self._accessible_playbook_ids(user)
        return (
            Activity.objects.filter(workflow__playbook_id__in=ids)
            .filter(Q(name__icontains=query) | Q(guidance__icontains=query))
            .select_related("workflow", "workflow__playbook")
            .order_by("workflow__playbook__name", "workflow__order", "order")
        )

    def _search_artifacts(self, query: str, user) -> QuerySet[Artifact]:
        ids = self._accessible_playbook_ids(user)
        return (
            Artifact.objects.filter(playbook_id__in=ids)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("playbook")
            .order_by("playbook__name", "name")
        )

    def _search_skills(self, query: str, user) -> QuerySet[Skill]:
        ids = self._accessible_playbook_ids(user)
        return (
            Skill.objects.filter(playbook_id__in=ids)
            .filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(capability_domain__icontains=query)
                | Q(technology_stack__icontains=query)
            )
            .select_related("playbook")
            .order_by("playbook__name", "title")
        )

    def _search_agents(self, query: str, user) -> QuerySet[Agent]:
        ids = self._accessible_playbook_ids(user)
        return (
            Agent.objects.filter(playbook_id__in=ids)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("playbook")
            .order_by("playbook__name", "name")
        )

    def _search_rules(self, query: str, user) -> QuerySet[Rule]:
        ids = self._accessible_playbook_ids(user)
        return (
            Rule.objects.filter(playbook_id__in=ids)
            .filter(
                Q(title__icontains=query)
                | Q(slug__icontains=query)
                | Q(content__icontains=query)
            )
            .select_related("playbook")
            .order_by("playbook__name", "title")
        )

    def _serialize_result(self, entity_key: str, instance: Any, query: str) -> SearchResultRow:
        meta = next(m for m in SEARCH_ENTITY_META if m["key"] == entity_key)
        title, context, snippet, url = self._result_fields(entity_key, instance)
        singular = ENTITY_TESTID_SINGULAR[entity_key]
        pk = getattr(instance, "pk", getattr(instance, "id", 0))
        return {
            "testid": f"global-search-result-{singular}-{pk}",
            "title": title,
            "title_html": highlight_search_term(title, query),
            "context_html": highlight_search_term(context, query),
            "snippet_html": highlight_search_term(snippet, query),
            "type_label": meta["label_singular"],
            "icon": meta["icon"],
            "url": url,
        }

    def _result_fields(self, entity_key: str, instance: Any) -> tuple[str, str, str, str]:
        if entity_key == "playbooks":
            pb: Playbook = instance
            author = pb.author.get_full_name() or pb.author.username
            category = pb.category or pb.get_status_display()
            context = f"{author} · v{pb.version} · {category}"
            snippet = _truncate_snippet(_plain_text(pb.description))
            url = reverse("playbook_detail", kwargs={"pk": pb.pk})
            return pb.name, context, snippet, url

        if entity_key == "workflows":
            wf: Workflow = instance
            count = wf.get_activity_count()
            context = f"{wf.playbook.name} · {count} activities"
            snippet = _truncate_snippet(_plain_text(wf.description))
            url = reverse(
                "workflow_detail",
                kwargs={"playbook_pk": wf.playbook.pk, "pk": wf.pk},
            )
            return wf.name, context, snippet, url

        if entity_key == "phases":
            phase: Phase = instance
            context = phase.playbook.name
            snippet = _truncate_snippet(_plain_text(phase.description))
            url = reverse("phase_detail", kwargs={"playbook_pk": phase.playbook.pk, "phase_pk": phase.pk})
            return phase.name, context, snippet, url

        if entity_key == "activities":
            act: Activity = instance
            pb_name = act.workflow.playbook.name
            wf_name = act.workflow.name
            context = f"{pb_name} › {wf_name}"
            snippet = _truncate_snippet(_plain_text(act.guidance))
            url = reverse(
                "activity_detail",
                kwargs={
                    "playbook_pk": act.workflow.playbook.pk,
                    "workflow_pk": act.workflow.pk,
                    "activity_pk": act.pk,
                },
            )
            return act.name, context, snippet, url

        if entity_key == "artifacts":
            art: Artifact = instance
            context = art.playbook.name
            snippet = _truncate_snippet(_plain_text(art.description))
            url = reverse("artifact_detail", kwargs={"pk": art.pk})
            return art.name, context, snippet, url

        if entity_key == "skills":
            skill: Skill = instance
            parts = [p for p in (skill.capability_domain, skill.technology_stack) if p]
            context = " · ".join(parts) if parts else skill.playbook.name
            snippet = _truncate_snippet(_plain_text(skill.content))
            url = reverse(
                "skill_detail",
                kwargs={"playbook_pk": skill.playbook.pk, "skill_pk": skill.pk},
            )
            return skill.title, context, snippet, url

        if entity_key == "agents":
            agent: Agent = instance
            context = agent.playbook.name
            snippet = _truncate_snippet(_plain_text(agent.description))
            url = reverse("agent_detail", kwargs={"pk": agent.pk})
            return agent.name, context, snippet, url

        rule: Rule = instance
        apply_label = "yes" if rule.always_apply else "no"
        context = f"{rule.playbook.name} · always_apply: {apply_label}"
        snippet = _truncate_snippet(_plain_text(rule.content))
        url = reverse(
            "rule_detail",
            kwargs={"playbook_pk": rule.playbook.pk, "rule_pk": rule.pk},
        )
        return rule.title, context, snippet, url
