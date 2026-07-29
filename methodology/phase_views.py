"""
Phase CRUD views for Mimir methodology app.

Handles create, read, update, delete operations for Phase entities.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from methodology.models import Playbook, Phase
from methodology.services.phase_service import PhaseService
from methodology.services.playbook_service import PlaybookService
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.utils.guest_auth import guest_read_or_login_required
from methodology.utils.playbook_access import playbook_readable_or_404

logger = logging.getLogger(__name__)

# ─── NO ORM IN VIEWS ────────────────────────────────────────────────────────
# Views are thin controllers. NEVER query the ORM directly here.
# All data access must go through services in methodology/services/.
# Both views and MCP tools drink from the same service well.
# ────────────────────────────────────────────────────────────────────────────


# ==================== LIST ====================

@guest_read_or_login_required
def phase_list_global(request):
    """
    Global phases list — all phases across all playbooks owned by the user.

    Supports:
    - ``?q=`` — search (matches name and description)
    - ``?playbook=<id>`` — limit to phases in that playbook (must be readable)

    Anonymous guests see phases from released public playbooks only.

    Template: phases/list_global.html
    Template Context:
        - phases: QuerySet of Phase instances (filtered by query if provided)
        - query: Current search string
        - filter_playbook: Playbook instance if ``playbook`` query param applied, else None
        - total_count: Total phases before filtering
        - is_guest_browse: True for anonymous session

    :param request: Django request object
    :return: Rendered global list template
    """
    query = request.GET.get('q', '').strip()
    filter_playbook = _resolve_phase_list_playbook_filter(request)

    if request.user.is_authenticated:
        phases, total_count = PhaseService.list_phases_global(
            request.user,
            query=query or None,
            playbook_filter=filter_playbook,
        )
        is_guest_browse = False
        user_label = request.user.username
    else:
        from methodology.services.guest_browse_service import list_global_phases_for_guest

        phases, total_count = list_global_phases_for_guest(
            query=query or None,
            playbook_filter=filter_playbook,
        )
        is_guest_browse = True
        user_label = "anonymous"

    log_extra = []
    if filter_playbook is not None:
        log_extra.append(f"playbook_id={filter_playbook.pk}")
    if query:
        log_extra.append(f"query={query!r}")
    logger.info(
        "User %s viewing global phase list%s",
        user_label,
        (" (" + ", ".join(log_extra) + ")") if log_extra else "",
    )

    context = {
        'phases': phases,
        'query': query,
        'filter_playbook': filter_playbook,
        'total_count': total_count,
        'is_guest_browse': is_guest_browse,
    }
    return render(request, 'phases/list_global.html', context)


def _resolve_phase_list_playbook_filter(request):
    """
    Parse optional ``playbook`` query param for :func:`phase_list_global`.

    :returns: Readable :class:`Playbook` or ``None`` if missing/invalid/not accessible
    """
    raw = request.GET.get('playbook', '').strip()
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    if not raw:
        return None
    try:
        pk = int(raw)
    except ValueError:
        logger.info(
            "Ignoring invalid playbook query param for phase_list_global user=%s raw=%r",
            user_label,
            raw,
        )
        return None
    if request.user.is_authenticated:
        try:
            return PlaybookService.get_playbook(pk, request.user)
        except Exception:
            logger.info(
                "Playbook filter not applied (missing or not accessible) user=%s playbook=%s",
                user_label,
                pk,
            )
            return None
    try:
        return playbook_readable_or_404(request, pk)
    except Http404:
        logger.info(
            "Playbook filter not applied (missing or not accessible) user=%s playbook=%s",
            user_label,
            pk,
        )
        return None


@guest_read_or_login_required
def phase_list(request, playbook_pk):
    """
    Display list of phases for a playbook.
    
    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered phase list template
    """
    playbook = playbook_readable_or_404(request, playbook_pk)
    phases = PhaseService.list_phases(playbook_pk, request.user)
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info("User %s viewing phases for playbook %s", user_label, playbook_pk)
    
    context = {
        'playbook': playbook,
        'phases': phases,
        'is_guest_browse': not request.user.is_authenticated,
    }
    return render(request, 'phases/list.html', context)


# ==================== CREATE ====================

@login_required
def phase_create(request, playbook_pk):
    """
    Create a new phase for a playbook.
    
    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered create form or redirect to list on success
    """
    playbook = get_object_or_404(Playbook, pk=playbook_pk, author=request.user)
    
    # Check if playbook is released
    if playbook.status == 'released':
        messages.error(request, 'Cannot create phases in a released playbook.')
        return redirect('phase_list', playbook_pk=playbook_pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        order_str = request.POST.get('order', '').strip()
        
        # Validate order
        order = None
        if order_str:
            try:
                order = int(order_str)
            except ValueError:
                messages.error(request, 'Order must be a number.')
                return _render_create_form(request, playbook, request.POST, {'order': 'Must be a number'})
        
        # Create phase
        try:
            phase = PhaseService.create_phase(
                playbook_id=playbook_pk,
                name=name,
                description=description,
                order=order,
                user=request.user
            )
            logger.info(f"Phase '{name}' created successfully in playbook {playbook_pk}")
            messages.success(request, f"Phase '{phase.name}' created successfully!")
            return redirect('phase_list', playbook_pk=playbook_pk)
            
        except ValidationError as e:
            logger.warning(f"Phase creation validation error: {str(e)}")
            messages.error(request, str(e))
            return _render_create_form(request, playbook, request.POST, {})
    
    # GET request - show form
    return _render_create_form(request, playbook, {}, {})


def _render_create_form(request, playbook, form_data, errors):
    """Helper to render create form with context."""
    context = {
        'playbook': playbook,
        'form_data': form_data,
        'errors': errors,
    }
    return render(request, 'phases/create.html', context)


# ==================== DETAIL ====================

@guest_read_or_login_required
def phase_detail(request, playbook_pk, phase_pk):
    """
    Display phase details with activities.
    
    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param phase_pk: Phase primary key
    :return: Rendered phase detail template
    """
    playbook = playbook_readable_or_404(request, playbook_pk)
    try:
        phase_data = PhaseService.get_phase_with_activities(phase_pk, request.user)
    except PermissionDenied:
        raise Http404()

    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info("User %s viewing phase %s", user_label, phase_pk)
    
    # Transform workflow_activities dict to list of dicts for template
    CopyPromptService.attach_activity_copy_prompts_grouped(
        phase_data['workflow_activities']
    )
    workflow_activities_list = [
        {'workflow': workflow, 'activities': activities}
        for workflow, activities in phase_data['workflow_activities'].items()
    ]
    
    phase = phase_data['phase']
    context = {
        'playbook': playbook,
        'phase': phase,
        'workflow_activities': workflow_activities_list,
        'artifacts': phase_data['artifacts'],
        'can_edit': playbook.can_edit(request.user) if request.user.is_authenticated else False,
        'is_guest_browse': not request.user.is_authenticated,
    }
    return render(request, 'phases/detail.html', context)


# ==================== EDIT ====================

@login_required
def phase_edit(request, playbook_pk, phase_pk):
    """
    Edit an existing phase.
    
    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param phase_pk: Phase primary key
    :return: Rendered edit form or redirect to detail on success
    """
    playbook = get_object_or_404(Playbook, pk=playbook_pk, author=request.user)
    phase = get_object_or_404(Phase, pk=phase_pk, playbook=playbook)
    
    # Check if playbook is released
    if playbook.status == 'released':
        messages.error(request, 'Cannot edit phases in a released playbook.')
        return redirect('phase_detail', playbook_pk=playbook_pk, phase_pk=phase_pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        order_str = request.POST.get('order', '').strip()
        
        # Validate order
        order = None
        if order_str:
            try:
                order = int(order_str)
            except ValueError:
                messages.error(request, 'Order must be a number.')
                return _render_edit_form(request, playbook, phase, request.POST, {'order': 'Must be a number'})
        
        # Update phase
        try:
            update_fields = {}
            if name:
                update_fields['name'] = name
            if description is not None:  # Allow empty string to clear description
                update_fields['description'] = description
            if order is not None:
                update_fields['order'] = order
            
            update_fields['user'] = request.user
            PhaseService.update_phase(phase_pk, **update_fields)
            
            logger.info(f"Phase {phase_pk} updated successfully")
            messages.success(request, f"Phase '{name}' updated successfully!")
            return redirect('phase_detail', playbook_pk=playbook_pk, phase_pk=phase_pk)
            
        except ValidationError as e:
            logger.warning(f"Phase edit validation error: {str(e)}")
            messages.error(request, str(e))
            return _render_edit_form(request, playbook, phase, request.POST, {})
    
    # GET request - show form with current values
    form_data = {
        'name': phase.name,
        'description': phase.description,
        'order': phase.order,
    }
    return _render_edit_form(request, playbook, phase, form_data, {})


def _render_edit_form(request, playbook, phase, form_data, errors):
    """Helper to render edit form with context."""
    context = {
        'playbook': playbook,
        'phase': phase,
        'form_data': form_data,
        'errors': errors,
    }
    return render(request, 'phases/edit.html', context)


# ==================== DELETE ====================

@login_required
def phase_delete(request, playbook_pk, phase_pk):
    """
    Delete a phase.
    
    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :param phase_pk: Phase primary key
    :return: Rendered delete confirmation or redirect to list on success
    """
    playbook = get_object_or_404(Playbook, pk=playbook_pk, author=request.user)
    phase = get_object_or_404(Phase, pk=phase_pk, playbook=playbook)
    
    # Check if playbook is released
    if playbook.status == 'released':
        messages.error(request, 'Cannot delete phases in a released playbook.')
        return redirect('phase_detail', playbook_pk=playbook_pk, phase_pk=phase_pk)
    
    if request.method == 'POST':
        phase_name = phase.name
        
        try:
            PhaseService.delete_phase(phase_pk, request.user)
            logger.info(f"Phase {phase_pk} deleted successfully")
            messages.success(request, f"Phase '{phase_name}' deleted successfully!")
            return redirect('phase_list', playbook_pk=playbook_pk)
            
        except ValidationError as e:
            logger.warning(f"Phase deletion error: {str(e)}")
            messages.error(request, str(e))
            return redirect('phase_detail', playbook_pk=playbook_pk, phase_pk=phase_pk)
    
    # GET request - show confirmation
    # Get activity count for this phase
    activity_count = phase.activities.count()
    
    context = {
        'playbook': playbook,
        'phase': phase,
        'activity_count': activity_count,
    }
    return render(request, 'phases/delete.html', context)
