"""
Agent views for global list, create, and detail operations.

Provides a global list of all agents across playbooks owned by the user,
with search support via ?q= query parameter, plus playbook-scoped create
and per-agent detail views.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from methodology.models import Agent, Playbook
from methodology.services.agent_service import AgentService
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.utils.guest_auth import guest_read_or_login_required
from methodology.utils.playbook_access import playbook_readable_or_404

logger = logging.getLogger(__name__)

# ─── NO ORM IN VIEWS ────────────────────────────────────────────────────────
# Views are thin controllers. NEVER query the ORM directly here.
# All data access must go through services in methodology/services/.
# Both views and MCP tools drink from the same service well.
# ────────────────────────────────────────────────────────────────────────────


@guest_read_or_login_required
def agent_list_global(request):
    """
    Global agents list — all agents across all playbooks owned by the user.

    Supports search via ?q= query parameter (matches name and description).
    Anonymous guests see agents from released public playbooks only.

    Template: agents/list.html
    Template Context:
        - agents: QuerySet of Agent instances (filtered by query if provided)
        - query: Current search string
        - total_count: Total agents before filtering
        - is_guest_browse: True for anonymous session

    :param request: Django request object
    :return: Rendered global list template
    """
    query = request.GET.get('q', '').strip()

    if request.user.is_authenticated:
        agents = AgentService.search_agents(query=query, user=request.user)
        total_count = AgentService.search_agents(query='', user=request.user).count()
        is_guest_browse = False
        user_label = request.user.username
    else:
        from methodology.services.guest_browse_service import list_global_agents_for_guest

        agents = list_global_agents_for_guest(query=query or None)
        total_count = list_global_agents_for_guest().count()
        is_guest_browse = True
        user_label = "anonymous"

    logger.info(
        "User %s viewing global agent list%s",
        user_label,
        f", query={query!r}" if query else "",
    )

    CopyPromptService.attach_copy_prompts(
        agents, CopyPromptService.build_agent_prompt
    )

    context = {
        'agents': agents,
        'query': query,
        'total_count': total_count,
        'is_guest_browse': is_guest_browse,
    }
    return render(request, 'agents/list.html', context)


@guest_read_or_login_required
def agent_list_for_playbook(request, playbook_pk):
    playbook = playbook_readable_or_404(request, playbook_pk)
    agents = AgentService.list_agents_for_playbook(playbook_pk)
    cnt = agents.count()
    is_guest_browse = not request.user.is_authenticated
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info(
        'User %s viewing agents for playbook %s (count=%d)',
        user_label,
        playbook_pk,
        cnt,
    )
    CopyPromptService.attach_copy_prompts(
        agents, CopyPromptService.build_agent_prompt
    )

    return render(request, 'agents/playbook_list.html', {
        'playbook': playbook,
        'agents': agents,
        'can_edit': playbook.can_edit(request.user),
        'is_guest_browse': is_guest_browse,
    })


# ==================== CREATE ====================


@login_required
def agent_create(request, playbook_pk):
    """
    Create a new agent for a playbook.

    GET: Display create form.
    POST: Validate and create agent, redirect to playbook detail on success.

    Template: agents/create.html
    Template Context:
        - playbook: Playbook instance
        - form_data: Dict with submitted field values (on validation error)
        - errors: Dict with field-level error messages (on validation error)

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered form template or redirect
    :raises Http404: If playbook not found
    """
    playbook = get_object_or_404(Playbook, pk=playbook_pk)

    if not playbook.can_edit(request.user):
        reason = (
            "released_playbook_pip_required"
            if playbook.is_owned_by(request.user) and playbook.is_released
            else "not_owner"
        )
        logger.warning(
            "agent_create | branch | user=%s playbook=%s reason=%s",
            request.user.username,
            playbook_pk,
            reason,
        )
        messages.error(request, "You don't have permission to add agents to this playbook.")
        return redirect('playbook_detail', pk=playbook_pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        errors = _validate_agent_form(name)
        if not errors:
            try:
                agent = AgentService.create_agent(
                    playbook=playbook,
                    name=name,
                    description=description,
                )
                logger.info(
                    f"User {request.user.username} created agent '{name}' "
                    f"in playbook {playbook_pk}"
                )
                messages.success(request, f"Agent '{agent.name}' created successfully!")
                return redirect('agent_detail', pk=agent.pk)
            except ValidationError as e:
                logger.warning(f"Agent creation validation error: {e}")
                errors['name'] = str(e.message)

        return _render_create_form(request, playbook, request.POST, errors)

    logger.info(
        f"User {request.user.username} opening agent create form for playbook {playbook_pk}"
    )
    return _render_create_form(request, playbook, {}, {})


def _validate_agent_form(name):
    """
    Validate agent form fields and return dict of field-level errors.

    :param name: Agent name string from form submission
    :returns: Dict mapping field name to error message (empty if valid)
    :rtype: dict
    """
    errors = {}
    if not name:
        errors['name'] = 'This field is required.'
    elif len(name) > 200:
        errors['name'] = 'Agent name cannot exceed 200 characters'
    return errors


def _render_create_form(request, playbook, form_data, errors):
    """Render agent create form with context."""
    context = {
        'playbook': playbook,
        'form_data': form_data,
        'errors': errors,
    }
    return render(request, 'agents/create.html', context)


# ==================== DETAIL ====================


@guest_read_or_login_required
def agent_detail(request, pk):
    """
    Display agent details including associated activities.

    Template: agents/detail.html
    Template Context:
        - agent: Agent instance
        - playbook: Playbook instance
        - activities: QuerySet of Activity instances assigned to this agent
        - can_edit: Boolean indicating if user can edit

    :param request: Django request object
    :param pk: Agent primary key
    :return: Rendered detail template
    :raises Http404: If agent not found
    """
    try:
        agent = AgentService.get_agent_for_user(pk, request.user)
    except Agent.DoesNotExist:
        raise Http404()
    except (PermissionError, ObjectDoesNotExist):
        raise Http404()

    activities = AgentService.get_activities_for_agent(agent.pk)
    can_edit = agent.can_edit(request.user) if request.user.is_authenticated else False
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info("User %s viewing agent %s", user_label, pk)

    context = {
        'agent': agent,
        'playbook': agent.playbook,
        'activities': activities,
        'can_edit': can_edit,
        'is_guest_browse': not request.user.is_authenticated,
        'copy_prompt_text': CopyPromptService.build_agent_prompt(agent),
        'copy_prompt_text_testid': f"copy-prompt-text-agent-{agent.pk}",
    }
    if request.GET.get('embed') == '1':
        return render(request, 'agents/_embed.html', context)
    logger.info(
        "Agent detail rendered user=%s agent=%s playbook_status=%s can_edit=%s",
        user_label,
        pk,
        agent.playbook.status,
        can_edit,
    )
    return render(request, 'agents/detail.html', context)


# ==================== EDIT ====================


@login_required
def agent_edit(request, pk):
    """
    Edit existing agent.

    GET: Display edit form with pre-populated data.
    POST: Validate and update agent, redirect to detail view on success.

    Template: agents/edit.html
    Template Context:
        - agent: Agent instance being edited
        - form_data: Dict with current field values (GET) or user input (POST on error)
        - errors: Dict with field-level error messages (empty on GET, populated on POST error)
        - playbook: Playbook instance for breadcrumbs

    :param request: Django request object
    :param pk: Agent primary key
    :return: Rendered edit form template or redirect
    :raises Http404: If agent not found
    """
    try:
        agent = AgentService.get_agent_for_user(pk, request.user, write=True)
    except Agent.DoesNotExist:
        raise Http404()
    except (PermissionError, ObjectDoesNotExist):
        messages.error(request, "You don't have permission to edit this agent.")
        return redirect('agent_detail', pk=pk)

    if not agent.can_edit(request.user):
        logger.warning(
            "agent_edit | branch | user=%s agent=%s reason=released_playbook_pip_required",
            request.user.username,
            pk,
        )
        messages.error(request, "You don't have permission to edit this agent.")
        return redirect('agent_detail', pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        form_data = {'name': name, 'description': description}

        try:
            updated_agent = AgentService.update_agent(pk, name=name, description=description)
            logger.info(
                f"User {request.user.username} updated agent {pk} '{updated_agent.name}'"
            )
            messages.success(request, f'Agent "{updated_agent.name}" updated successfully.')
            return redirect('agent_detail', pk=pk)
        except ValidationError as e:
            errors = _extract_validation_errors(e)
            return _render_edit_form(request, agent, form_data, errors)

    form_data = {'name': agent.name, 'description': agent.description}
    logger.info(f"User {request.user.username} opening agent edit form for agent {pk}")
    return _render_edit_form(request, agent, form_data, {})


def _extract_validation_errors(exc):
    """
    Extract field-level errors from a ValidationError into a flat dict.

    :param exc: ValidationError raised by AgentService
    :returns: Dict mapping field name to first error message string
    :rtype: dict

    Example:
        >>> # exc.message_dict = {'name': ['Agent already exists']}
        >>> _extract_validation_errors(exc)
        {'name': 'Agent already exists'}
        >>> # exc with plain message: "Agent name cannot be empty"
        >>> _extract_validation_errors(exc)
        {'name': 'Agent name cannot be empty'}
    """
    if hasattr(exc, 'message_dict'):
        return {field: msgs[0] if isinstance(msgs, list) else msgs
                for field, msgs in exc.message_dict.items()}
    if hasattr(exc, 'messages') and exc.messages:
        return {'name': exc.messages[0]}
    return {'name': str(exc)}


def _render_edit_form(request, agent, form_data, errors):
    """
    Render agent edit form with context.

    :param request: Django request object
    :param agent: Agent instance being edited
    :param form_data: Dict with current or user-submitted field values
    :param errors: Dict mapping field names to error message strings
    :returns: Rendered agents/edit.html response
    :rtype: HttpResponse

    Example:
        >>> return _render_edit_form(request, agent, {'name': 'Reviewer'}, {'name': 'Required'})
    """
    context = {
        'agent': agent,
        'form_data': form_data,
        'errors': errors,
        'playbook': agent.playbook,
    }
    return render(request, 'agents/edit.html', context)


# ==================== DELETE ====================


@login_required
def agent_delete(request, pk):
    """
    Delete agent with HTMX confirmation modal.

    GET: Render delete confirmation modal partial with cascade warnings.
    POST: Delete agent (activities retain NULL agent), redirect to playbook detail.

    Template: agents/_delete_modal.html (GET only)
    Template Context:
        - agent: Agent instance to delete
        - activity_count: int total activities using this agent
        - activities: QuerySet of first 5 activities (for display)

    :param request: Django request object
    :param pk: Agent primary key
    :return: Rendered modal partial (GET) or redirect (POST)
    :raises Http404: If agent not found
    """
    try:
        agent = AgentService.get_agent_for_user(pk, request.user, write=True)
    except Agent.DoesNotExist:
        raise Http404()
    except (PermissionError, ObjectDoesNotExist):
        messages.error(request, "You don't have permission to delete this agent.")
        return redirect('agent_detail', pk=pk)

    if not agent.can_edit(request.user):
        logger.warning(
            "agent_delete | branch | user=%s agent=%s reason=released_playbook_pip_required",
            request.user.username,
            pk,
        )
        messages.error(request, "You don't have permission to delete this agent.")
        return redirect('agent_detail', pk=pk)

    if request.method == 'POST':
        playbook_id = agent.playbook_id
        agent_name = agent.name
        AgentService.delete_agent(pk)
        logger.info(
            f"User {request.user.username} deleted agent '{agent_name}' (id={pk})"
        )
        messages.success(request, f'Agent "{agent_name}" deleted successfully.')
        return redirect('playbook_detail', pk=playbook_id)

    activities = AgentService.get_activities_for_agent(agent.pk)[:5]
    activity_count = agent.get_activity_count()
    logger.info(
        f"User {request.user.username} opening delete modal for agent {pk}"
    )
    context = {
        'agent': agent,
        'activity_count': activity_count,
        'activities': activities,
    }
    return render(request, 'agents/_delete_modal.html', context)
