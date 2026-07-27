"""
Guest browse helpers for global entity list querysets.
"""

import logging

from django.db.models import Q

from methodology.models import Activity, Agent, Artifact, Phase, Rule, Skill, Workflow
from methodology.services.playbook_service import PlaybookService

logger = logging.getLogger(__name__)


def guest_playbook_ids():
    """Return playbook PKs readable by anonymous guests."""
    return PlaybookService.get_guest_readable_playbook_ids()


def list_global_workflows_for_guest():
    """Workflows in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Workflow.objects.filter(playbook_id__in=ids).select_related("playbook").order_by(
        "playbook__name", "order"
    )
    logger.info("Guest global workflows count=%s", qs.count())
    return qs


def list_global_activities_for_guest():
    """Activities in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Activity.objects.filter(workflow__playbook_id__in=ids).select_related(
        "workflow", "workflow__playbook", "phase"
    ).order_by("workflow__playbook__name", "workflow__order", "order")
    logger.info("Guest global activities count=%s", qs.count())
    return qs


def list_global_artifacts_for_guest(query=None):
    """Artifacts in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Artifact.objects.filter(playbook_id__in=ids).select_related(
        "playbook", "produced_by", "produced_by__workflow"
    ).order_by("playbook__name", "name")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    logger.info("Guest global artifacts count=%s", qs.count())
    return qs


def list_global_skills_for_guest(query=None):
    """Skills in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Skill.objects.filter(playbook_id__in=ids).select_related("playbook").order_by(
        "playbook__name", "title"
    )
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(content__icontains=query))
    logger.info("Guest global skills count=%s", qs.count())
    return qs


def list_global_agents_for_guest(query=None):
    """Agents in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Agent.objects.filter(playbook_id__in=ids).select_related("playbook").order_by(
        "playbook__name", "name"
    )
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    logger.info("Guest global agents count=%s", qs.count())
    return qs


def list_global_rules_for_guest(query=None):
    """Rules in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Rule.objects.filter(playbook_id__in=ids).select_related("playbook").order_by(
        "playbook__name", "title"
    )
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(content__icontains=query))
    logger.info("Guest global rules count=%s", qs.count())
    return qs


def list_global_phases_for_guest(query=None, playbook_filter=None):
    """Phases in released public playbooks."""
    ids = guest_playbook_ids()
    qs = Phase.objects.filter(playbook_id__in=ids).select_related("playbook")
    if playbook_filter is not None:
        qs = qs.filter(playbook_id=playbook_filter.pk)
    total_count = qs.count()
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    qs = qs.order_by("playbook__name", "order")
    logger.info("Guest global phases count=%s", qs.count())
    return qs, total_count
