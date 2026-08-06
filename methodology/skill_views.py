"""
Skill views for playbook-scoped CRUDLF operations.

Skills are playbook-scoped, reusable guides with capability_domain
and technology_stack metadata. Views use playbook_pk + skill_pk routing.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from methodology.models import Playbook, Skill
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.services.skill_service import SkillService
from methodology.utils.guest_auth import guest_read_or_login_required
from methodology.utils.playbook_access import playbook_can_submit_pip, playbook_readable_or_404

logger = logging.getLogger(__name__)

# ─── NO ORM IN VIEWS ────────────────────────────────────────────────────────
# Views are thin controllers. NEVER query the ORM directly here.
# All data access must go through services in methodology/services/.
# Both views and MCP tools drink from the same service well.
# ────────────────────────────────────────────────────────────────────────────


# ==================== HELPERS ====================

def _get_playbook_or_deny(request, playbook_pk):
    """Return playbook if readable; else Http404 (no existence leak)."""
    return playbook_readable_or_404(request, playbook_pk)


def _get_skill_in_playbook(playbook, skill_pk):
    """
    Get skill ensuring it belongs to the given playbook.

    :param playbook: Playbook instance
    :param skill_pk: Skill primary key
    :returns: Skill instance
    :raises Http404: If skill not found in this playbook
    """
    return get_object_or_404(Skill, pk=skill_pk, playbook=playbook)


# ==================== GLOBAL LIST ====================

@guest_read_or_login_required
def skill_list_global(request):
    """
    Global skills list — all skills across all playbooks owned by the user.

    Supports search via ?q= query parameter.
    Anonymous guests see skills from released public playbooks only.

    Template: skills/list.html
    Template Context:
        - skills: QuerySet of Skill instances
        - query: Current search string
        - total_count: Total skills before filtering
        - is_guest_browse: True for anonymous session

    :param request: Django request object
    :return: Rendered global list template
    """
    query = request.GET.get('q', '').strip()

    if request.user.is_authenticated:
        skills = SkillService.search_skills(query=query, user=request.user)
        total_count = SkillService.search_skills(query='', user=request.user).count()
        is_guest_browse = False
        user_label = request.user.username
    else:
        from methodology.services.guest_browse_service import list_global_skills_for_guest

        skills = list_global_skills_for_guest(query=query or None)
        total_count = list_global_skills_for_guest().count()
        is_guest_browse = True
        user_label = "anonymous"

    logger.info(
        "User %s viewing global skill list%s",
        user_label,
        f", query={query!r}" if query else '',
    )

    CopyPromptService.attach_copy_prompts(
        skills, CopyPromptService.build_skill_prompt
    )

    context = {
        'skills': skills,
        'query': query,
        'total_count': total_count,
        'is_guest_browse': is_guest_browse,
    }
    return render(request, 'skills/list.html', context)


# ==================== PLAYBOOK-SCOPED LIST ====================

@guest_read_or_login_required
def skill_list(request, playbook_pk):
    """
    List skills in a playbook with filtering.

    Query params: ?q=, ?domain=, ?stack=, ?unlinked=1

    Template: skills/playbook_list.html
    Template Context:
        - playbook: Playbook instance
        - skills: QuerySet annotated with activity_count
        - query, domain_filter, stack_filter, unlinked_only: filter state
        - domains, stacks: autocomplete values

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered list template or redirect
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    query = request.GET.get('q', '').strip()
    domain_filter = request.GET.get('domain', '').strip()
    stack_filter = request.GET.get('stack', '').strip()
    unlinked_only = request.GET.get('unlinked') == '1'

    skills = SkillService.list_skills_for_playbook(
        playbook_id=playbook_pk,
        capability_domain=domain_filter,
        technology_stack=stack_filter,
        search=query,
        unlinked_only=unlinked_only,
    )

    domains = SkillService.get_distinct_domains(playbook_pk)
    stacks = SkillService.get_distinct_stacks(playbook_pk)

    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info(
        "User %s listing skills in playbook %s [q=%s, domain=%s, stack=%s, unlinked=%s]",
        user_label,
        playbook_pk,
        query,
        domain_filter,
        stack_filter,
        unlinked_only,
    )

    CopyPromptService.attach_copy_prompts(
        skills, CopyPromptService.build_skill_prompt
    )

    context = {
        'playbook': playbook,
        'skills': skills,
        'query': query,
        'domain_filter': domain_filter,
        'stack_filter': stack_filter,
        'unlinked_only': unlinked_only,
        'domains': domains,
        'stacks': stacks,
        'can_edit': playbook.can_edit(request.user),
        'is_guest_browse': not request.user.is_authenticated,
    }
    return render(request, 'skills/playbook_list.html', context)


# ==================== CREATE ====================

@login_required
def skill_create(request, playbook_pk):
    """
    Create a new skill in a playbook.

    GET: Render empty create form with autocomplete data.
    POST: Validate and create; redirect to detail on success.

    Template: skills/create.html
    Template Context:
        - playbook: Playbook instance
        - form_data: Submitted POST data (for re-display on error)
        - errors: Dict of field -> error message
        - domains, stacks: autocomplete values

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered form or redirect
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    if not playbook.can_edit(request.user):
        messages.error(request, "You don't have permission to create skills in this playbook.")
        return redirect('playbook_list')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        capability_domain = request.POST.get('capability_domain', '').strip()
        technology_stack = request.POST.get('technology_stack', '').strip()

        try:
            skill = SkillService.create_skill(
                playbook=playbook,
                title=title,
                content=content,
                capability_domain=capability_domain,
                technology_stack=technology_stack,
            )
            messages.success(request, f"Skill '{skill.title}' created successfully!")
            return redirect('skill_detail', playbook_pk=playbook_pk, skill_pk=skill.pk)
        except ValidationError as e:
            logger.warning("Skill create validation error: %s", e)
            return _render_create_form(
                request, playbook,
                form_data=request.POST,
                errors={'title': str(e.message)},
            )

    return _render_create_form(request, playbook, form_data={}, errors={})


# ==================== DETAIL ====================

@guest_read_or_login_required
def skill_detail(request, playbook_pk, skill_pk):
    """
    View skill detail page with metadata and activity references.

    Template: skills/detail.html
    Template Context:
        - playbook: Playbook instance
        - skill: Skill instance
        - activities: activities referencing this skill
        - can_edit: Boolean

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param skill_pk: Skill primary key
    :return: Rendered detail template or redirect
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    skill = _get_skill_in_playbook(playbook, skill_pk)
    activities = SkillService.get_activities_for_skill(skill_pk)
    can_edit = playbook.can_edit(request.user) if request.user.is_authenticated else False
    can_submit_pip = playbook_can_submit_pip(playbook, request.user)
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )

    logger.info(
        "User %s viewing skill %s '%s' in playbook %s can_edit=%s can_submit_pip=%s",
        user_label,
        skill_pk,
        skill.title,
        playbook_pk,
        can_edit,
        can_submit_pip,
    )

    context = {
        'playbook': playbook,
        'skill': skill,
        'activities': activities,
        'can_edit': can_edit,
        'can_submit_pip': can_submit_pip,
        'is_guest_browse': not request.user.is_authenticated,
        'copy_prompt_text': CopyPromptService.build_skill_prompt(skill),
        'copy_prompt_text_testid': f"copy-prompt-text-skill-{skill.pk}",
    }
    if request.GET.get('embed') == '1':
        return render(request, 'skills/_embed.html', context)
    return render(request, 'skills/detail.html', context)


# ==================== EDIT ====================

@login_required
def skill_edit(request, playbook_pk, skill_pk):
    """
    Edit an existing skill.

    GET: Render pre-populated edit form.
    POST: Validate and update; redirect to detail on success.

    Template: skills/edit.html
    Template Context:
        - playbook: Playbook instance
        - skill: Skill instance
        - form_data: Current or submitted values
        - errors: Dict of field -> error message
        - domains, stacks: autocomplete values

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param skill_pk: Skill primary key
    :return: Rendered form or redirect
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    if not playbook.can_edit(request.user):
        messages.error(request, "You don't have permission to edit skills in this playbook.")
        return redirect('playbook_list')

    skill = _get_skill_in_playbook(playbook, skill_pk)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        capability_domain = request.POST.get('capability_domain', '').strip()
        technology_stack = request.POST.get('technology_stack', '').strip()

        try:
            skill = SkillService.update_skill(
                skill.pk,
                title=title,
                content=content,
                capability_domain=capability_domain,
                technology_stack=technology_stack,
            )
            messages.success(request, f"Skill '{skill.title}' updated successfully!")
            return redirect('skill_detail', playbook_pk=playbook_pk, skill_pk=skill.pk)
        except ValidationError as e:
            logger.warning("Skill edit validation error: %s", e)
            return _render_edit_form(
                request, playbook, skill,
                form_data=request.POST,
                errors={'title': str(e.message)},
            )

    form_data = {
        'title': skill.title,
        'content': skill.content,
        'capability_domain': skill.capability_domain,
        'technology_stack': skill.technology_stack,
    }
    return _render_edit_form(request, playbook, skill, form_data=form_data, errors={})


# ==================== DELETE ====================

@login_required
def skill_delete_confirm(request, playbook_pk, skill_pk):
    """
    Return the delete confirmation modal partial (loaded via HTMX).

    Template: skills/_delete_modal.html

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param skill_pk: Skill primary key
    :return: Rendered modal partial
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    skill = _get_skill_in_playbook(playbook, skill_pk)
    activities = SkillService.get_activities_for_skill(skill_pk)

    from django.urls import reverse
    delete_url = reverse('skill_delete', kwargs={
        'playbook_pk': playbook_pk,
        'skill_pk': skill_pk,
    })

    context = {
        'playbook': playbook,
        'skill': skill,
        'activities': activities,
        'delete_url': delete_url,
    }
    return render(request, 'skills/_delete_modal.html', context)


@login_required
def skill_delete(request, playbook_pk, skill_pk):
    """
    Delete a skill (POST only).

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param skill_pk: Skill primary key
    :return: Redirect to playbook skill list
    """
    playbook = _get_playbook_or_deny(request, playbook_pk)

    if not playbook.can_edit(request.user):
        messages.error(request, "You don't have permission to delete skills in this playbook.")
        return redirect('playbook_list')

    skill = _get_skill_in_playbook(playbook, skill_pk)
    title = skill.title

    SkillService.delete_skill(skill.pk)
    messages.success(request, f"Skill '{title}' deleted successfully.")
    return redirect('skill_list_playbook', playbook_pk=playbook_pk)


# ==================== PRIVATE FORM HELPERS ====================

def _render_create_form(request, playbook, form_data, errors):
    """
    Render the skill create form template with context.

    :param request: Django request object
    :param playbook: Playbook instance
    :param form_data: Dict of current field values
    :param errors: Dict of field -> error message
    :return: Rendered create form response
    """
    domains = SkillService.get_distinct_domains(playbook.pk)
    stacks = SkillService.get_distinct_stacks(playbook.pk)

    context = {
        'playbook': playbook,
        'form_data': form_data,
        'errors': errors,
        'domains': domains,
        'stacks': stacks,
    }
    return render(request, 'skills/create.html', context)


def _render_edit_form(request, playbook, skill, form_data, errors):
    """
    Render the skill edit form template with context.

    :param request: Django request object
    :param playbook: Playbook instance
    :param skill: Skill instance
    :param form_data: Dict of current field values
    :param errors: Dict of field -> error message
    :return: Rendered edit form response
    """
    domains = SkillService.get_distinct_domains(playbook.pk)
    stacks = SkillService.get_distinct_stacks(playbook.pk)

    context = {
        'playbook': playbook,
        'skill': skill,
        'form_data': form_data,
        'errors': errors,
        'domains': domains,
        'stacks': stacks,
    }
    return render(request, 'skills/edit.html', context)
