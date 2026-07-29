"""
Artifact views for CRUD operations.

Provides views for creating, viewing, and editing artifacts within playbooks.
"""

import logging
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError

from methodology.models import Playbook, Artifact
from methodology.services.artifact_service import ArtifactService
from methodology.services.activity_service import ActivityService
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.utils.guest_auth import guest_read_or_login_required
from methodology.utils.playbook_access import playbook_readable_or_404

logger = logging.getLogger(__name__)

# ─── NO ORM IN VIEWS ────────────────────────────────────────────────────────
# Views are thin controllers. NEVER query the ORM directly here.
# All data access must go through services in methodology/services/.
# Both views and MCP tools drink from the same service well.
# ────────────────────────────────────────────────────────────────────────────


# ==================== GLOBAL LIST ====================


@guest_read_or_login_required
def artifact_list_global(request):
    """
    Global artifacts list — all artifacts across all playbooks owned by the user.
    
    Supports search via ?q= query parameter (matches name and description).
    Anonymous guests see artifacts from released public playbooks only.
    
    Template: artifacts/list_global.html
    Template Context:
        - artifacts: QuerySet of Artifact instances (filtered by query if provided)
        - query: Current search string
        - total_count: Total artifacts before filtering
        - is_guest_browse: True for anonymous session
    
    :param request: Django request object
    :return: Rendered global list template
    """
    query = request.GET.get('q', '').strip()

    if request.user.is_authenticated:
        artifacts = ArtifactService.list_artifacts_global(request.user, query=query or None)
        total_count = ArtifactService.list_artifacts_global(request.user).count()
        is_guest_browse = False
        user_label = request.user.username
    else:
        from methodology.services.guest_browse_service import list_global_artifacts_for_guest

        artifacts = list_global_artifacts_for_guest(query=query or None)
        total_count = list_global_artifacts_for_guest().count()
        is_guest_browse = True
        user_label = "anonymous"

    logger.info(
        "User %s viewing global artifact list%s",
        user_label,
        f", query={query!r}" if query else "",
    )

    CopyPromptService.attach_copy_prompts(
        artifacts, CopyPromptService.build_artifact_prompt
    )

    context = {
        'artifacts': artifacts,
        'query': query,
        'total_count': total_count,
        'is_guest_browse': is_guest_browse,
    }
    return render(request, 'artifacts/list_global.html', context)



# ==================== CREATE ====================


@login_required
def artifact_create(request, playbook_pk):
    """
    Create new artifact for playbook.

    GET: Display create form
    POST: Validate and create artifact, redirect to playbook detail

    Template: artifacts/create.html
    Template Context:
        - playbook: Playbook instance
        - activities: QuerySet of Activity instances for producer selection
        - artifact_types: List of type choices
        - form_data: Dict with form values (on validation error)
        - errors: Dict with field errors (on validation error)

    :param request: Django request object
    :param playbook_pk: Playbook primary key
    :return: Rendered form template or redirect
    :raises Http404: If playbook not found
    """
    logger.info(
        f"User {request.user.username} accessing artifact create for playbook {playbook_pk}"
    )

    # Get playbook with permission check
    playbook = get_object_or_404(Playbook, pk=playbook_pk)

    # Check edit permission
    if not playbook.is_owned_by(request.user):
        logger.warning(
            f"User {request.user.username} attempted to create artifact without permission"
        )
        messages.error(
            request, "You don't have permission to add artifacts to this playbook."
        )
        return redirect("playbook_detail", pk=playbook_pk)

    if request.method == "POST":
        # Extract form data
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        artifact_type = request.POST.get("type", "Document").strip()
        is_required = request.POST.get("is_required") == "on"
        produced_by_id = request.POST.get("produced_by", "").strip()
        template_file = request.FILES.get("template_file")

        # Get producer activity
        if not produced_by_id:
            messages.error(request, "Producer activity is required.")
            return _render_create_form(request, playbook, request.POST, {})

        try:
            produced_by = ActivityService.get_activity_for_playbook(
                int(produced_by_id), playbook
            )
        except (ValueError, Exception):
            messages.error(request, "Invalid producer activity selected.")
            return _render_create_form(request, playbook, request.POST, {})

        # Validate and create
        try:
            artifact = ArtifactService.create_artifact(
                playbook=playbook,
                produced_by=produced_by,
                name=name,
                description=description,
                type=artifact_type,
                is_required=is_required,
                template_file=template_file,
            )
            logger.info(
                f"Artifact '{name}' created successfully in playbook {playbook_pk}"
            )
            messages.success(
                request, f"Artifact '{artifact.name}' created successfully!"
            )
            return redirect("playbook_detail", pk=playbook_pk)

        except ValidationError as e:
            logger.warning(f"Artifact creation validation error: {str(e)}")
            messages.error(request, str(e))
            return _render_create_form(request, playbook, request.POST, {})

    # GET request - show form
    return _render_create_form(request, playbook, {}, {})


def _render_create_form(request, playbook, form_data, errors):
    """Helper to render create form with context."""
    activities = ActivityService.list_activities_for_playbook(playbook.pk, request.user)

    context = {
        "playbook": playbook,
        "activities": activities,
        "artifact_types": Artifact.ARTIFACT_TYPES,
        "form_data": form_data,
        "errors": errors,
    }
    return render(request, "artifacts/create.html", context)


# ==================== VIEW ====================


@guest_read_or_login_required
def artifact_detail(request, pk):
    """
    Display artifact details.

    Displays full artifact information including name, description, type,
    producer activity, consumer activities, and template file.

    Template: artifacts/detail.html
    Template Context:
        - artifact: Artifact instance
        - playbook: Playbook instance
        - producer: Activity instance (artifact.produced_by)
        - consumers: QuerySet of ArtifactInput instances
        - can_edit: Boolean indicating if user can edit

    :param request: Django request object
    :param pk: Artifact primary key
    :return: Rendered detail template
    :raises Http404: If artifact not found
    """
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info("User %s viewing artifact %s", user_label, pk)

    try:
        artifact = ArtifactService.get_artifact_for_user(pk, request.user)
    except Exception:
        raise Http404()

    # Get consumers
    consumers = ArtifactService.get_artifact_consumers(artifact)
    can_edit = (
        artifact.playbook.is_owned_by(request.user)
        if request.user.is_authenticated
        else False
    )

    context = {
        "artifact": artifact,
        "playbook": artifact.playbook,
        "producer": artifact.produced_by,
        "consumers": consumers,
        "can_edit": can_edit,
        "is_guest_browse": not request.user.is_authenticated,
        "copy_prompt_text": CopyPromptService.build_artifact_prompt(artifact),
        "copy_prompt_text_testid": f"copy-prompt-text-artifact-{artifact.pk}",
    }
    if request.GET.get('embed') == '1':
        return render(request, 'artifacts/_embed.html', context)
    logger.info("Artifact detail rendered for user %s", user_label)
    return render(request, "artifacts/detail.html", context)


# ==================== EDIT ====================


@login_required
def artifact_edit(request, pk):
    """
    Edit existing artifact.

    GET: Display edit form with current values
    POST: Validate and update artifact, redirect to detail

    Template: artifacts/edit.html
    Template Context:
        - artifact: Artifact instance
        - playbook: Playbook instance
        - activities: QuerySet of Activity instances
        - artifact_types: List of type choices
        - form_data: Dict with form values (on validation error)
        - errors: Dict with field errors (on validation error)

    :param request: Django request object
    :param pk: Artifact primary key
    :return: Rendered form template or redirect
    :raises Http404: If artifact not found
    """
    logger.info(f"User {request.user.username} accessing artifact edit for {pk}")

    try:
        artifact = ArtifactService.get_artifact_for_user(pk, request.user, write=True)
    except Exception:
        messages.error(request, "You don't have permission to edit this artifact.")
        return redirect("artifact_detail", pk=pk)

    if request.method == "POST":
        # Extract form data
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        artifact_type = request.POST.get("type", "Document").strip()
        is_required = request.POST.get("is_required") == "on"
        produced_by_id = request.POST.get("produced_by", "").strip()
        template_file = request.FILES.get("template_file")

        # Prepare update data
        update_data = {
            "name": name,
            "description": description,
            "type": artifact_type,
            "is_required": is_required,
        }

        # Handle producer change
        if produced_by_id:
            try:
                produced_by = ActivityService.get_activity_for_playbook(
                    int(produced_by_id), artifact.playbook
                )
                update_data["produced_by"] = produced_by
            except (ValueError, Exception):
                messages.error(request, "Invalid producer activity selected.")
                return _render_edit_form(request, artifact, request.POST, {})

        # Handle template file
        if template_file:
            update_data["template_file"] = template_file

        # Validate and update
        try:
            artifact = ArtifactService.update_artifact(pk, **update_data)
            logger.info(f"Artifact '{name}' updated successfully")
            messages.success(
                request, f"Artifact '{artifact.name}' updated successfully!"
            )
            return redirect("artifact_detail", pk=pk)

        except ValidationError as e:
            logger.warning(f"Artifact update validation error: {str(e)}")
            messages.error(request, str(e))
            return _render_edit_form(request, artifact, request.POST, {})

    # GET request - show form with current values
    form_data = {
        "name": artifact.name,
        "description": artifact.description,
        "type": artifact.type,
        "is_required": artifact.is_required,
        "produced_by": artifact.produced_by_id,
    }
    return _render_edit_form(request, artifact, form_data, {})


def _render_edit_form(request, artifact, form_data, errors):
    """Helper to render edit form with context."""
    activities = ActivityService.list_activities_for_playbook(
        artifact.playbook.pk, request.user
    )

    context = {
        "artifact": artifact,
        "playbook": artifact.playbook,
        "activities": activities,
        "artifact_types": Artifact.ARTIFACT_TYPES,
        "form_data": form_data,
        "errors": errors,
    }
    return render(request, "artifacts/edit.html", context)


# ==================== LIST ====================


@guest_read_or_login_required
def artifact_list(request, playbook_id):
    """
    Display artifacts list for playbook with search/filter.

    :param request: Django HttpRequest with GET params
    :param playbook_id: Playbook ID as int from URL
    :returns: HttpResponse with rendered template

    Template: artifacts/list.html
    Context:
        - playbook: Playbook instance
        - artifacts: QuerySet of Artifact instances (filtered)
        - search_query: str or None. Example: "API"
        - type_filter: str or None. Example: "Document"
        - required_filter: bool or None. Example: True
        - activity_filter: int or None (activity ID)
        - activities: QuerySet of Activity instances for filter dropdown
        - total_count: int - total artifacts before filtering
        - filtered_count: int - artifacts after filtering

    GET Parameters:
        - q: Search query for name/description
        - type: Type filter
        - required: Required filter ("true"/"false")
        - activity: Activity ID filter
    """
    user_label = (
        request.user.username if request.user.is_authenticated else "anonymous"
    )
    logger.info(
        "User %s accessing artifact list for playbook %s",
        user_label,
        playbook_id,
    )

    playbook = playbook_readable_or_404(request, playbook_id)

    filters = _parse_list_filters(request.GET)
    total_count = ArtifactService.count_artifacts_for_playbook(playbook)
    
    artifacts = ArtifactService.search_artifacts(
        playbook=playbook,
        search_query=filters['search_query'],
        type_filter=filters['type_filter'],
        required_filter=filters['required_filter'],
        activity_filter=filters['activity_filter'],
    )
    CopyPromptService.attach_copy_prompts(
        artifacts, CopyPromptService.build_artifact_prompt
    )

    context = _build_list_context(
        playbook, request.user, artifacts, filters, total_count
    )
    context["is_guest_browse"] = not request.user.is_authenticated
    
    logger.info(
        f"Artifact list rendered: {artifacts.count()} artifacts "
        f"(filters: q={filters['search_query']}, type={filters['type_filter']}, "
        f"required={filters['required_filter']}, activity={filters['activity_filter']})"
    )

    return render(request, "artifacts/list.html", context)


def _get_playbook_with_permission_check(request, playbook_id):
    """Get playbook and check user permissions."""
    playbook = get_object_or_404(Playbook, pk=playbook_id)

    if not playbook.can_view(request.user):
        logger.warning(
            f"User {request.user.username} attempted to access artifact list without permission"
        )
        messages.error(request, "You don't have permission to view this playbook.")
        return None

    return playbook


def _parse_list_filters(get_params):
    """Parse filter parameters from GET request."""
    search_query = get_params.get("q", "").strip() or None
    type_filter = get_params.get("type", "").strip() or None
    required_param = get_params.get("required", "").strip()
    activity_param = get_params.get("activity", "").strip()

    # Parse required filter
    required_filter = None
    if required_param == "true":
        required_filter = True
    elif required_param == "false":
        required_filter = False

    # Parse activity filter
    activity_filter = None
    if activity_param:
        try:
            activity_filter = int(activity_param)
        except ValueError:
            pass

    return {
        'search_query': search_query,
        'type_filter': type_filter,
        'required_filter': required_filter,
        'activity_filter': activity_filter,
    }


def _build_list_context(playbook, user, artifacts, filters, total_count):
    """Build template context for artifact list."""
    activities = ActivityService.list_activities_for_playbook(playbook.pk, user)

    return {
        "playbook": playbook,
        "artifacts": artifacts,
        "search_query": filters['search_query'],
        "type_filter": filters['type_filter'],
        "required_filter": filters['required_filter'],
        "activity_filter": filters['activity_filter'],
        "activities": activities,
        "total_count": total_count,
        "filtered_count": artifacts.count(),
        "artifact_types": Artifact.ARTIFACT_TYPES,
    }


# ==================== DELETE ====================


@login_required
def artifact_delete(request, pk):
    """
    Delete artifact with confirmation modal.

    :param request: Django HttpRequest with GET/POST
    :param pk: Artifact ID as int from URL
    :returns: HttpResponse with modal or redirect

    GET: Returns delete confirmation modal
    POST: Deletes artifact and redirects to list

    Template: artifacts/_delete_modal.html (for GET)
    Context:
        - artifact: Artifact instance
        - consumer_count: int - number of consuming activities
        - consumers: QuerySet of ArtifactInput instances
        - has_template: bool - whether artifact has template file
    """
    logger.info(f"User {request.user.username} accessing artifact delete for {pk}")

    artifact = _get_artifact_with_permission_check(request, pk)
    if not artifact:
        return redirect("artifact_detail", pk=pk)

    if request.method == "POST":
        return _handle_artifact_deletion(request, artifact)

    # GET request - show confirmation modal
    return _render_delete_modal(request, artifact)


def _get_artifact_with_permission_check(request, pk):
    """Get artifact with optimized queries and check permissions."""
    try:
        return ArtifactService.get_artifact_for_user(pk, request.user, write=True)
    except Exception:
        logger.warning(
            f"User {request.user.username} attempted to delete artifact without permission"
        )
        messages.error(request, "You don't have permission to delete this artifact.")
        return None


def _handle_artifact_deletion(request, artifact):
    """Handle POST request to delete artifact."""
    playbook_id = artifact.playbook.id
    artifact_name = artifact.name

    try:
        result = ArtifactService.delete_artifact(artifact)
        logger.info(
            f"User {request.user.username} deleted artifact '{artifact_name}': {result}"
        )
        messages.success(
            request,
            f"Artifact '{artifact_name}' deleted successfully! "
            f"({result['consumers_cleared']} consumer(s) cleared)",
        )
        return redirect("artifact_list", playbook_id=playbook_id)

    except Exception as e:
        logger.error(f"Failed to delete artifact {artifact.pk}: {str(e)}")
        messages.error(request, f"Failed to delete artifact: {str(e)}")
        return redirect("artifact_detail", pk=artifact.pk)


def _render_delete_modal(request, artifact):
    """Render delete confirmation modal with context."""
    consumers = ArtifactService.get_artifact_consumers(artifact)
    consumer_count = consumers.count()
    has_template = bool(artifact.template_file)

    logger.info(
        f"Delete modal displayed: consumers={consumer_count}, has_template={has_template}"
    )

    context = {
        "artifact": artifact,
        "consumer_count": consumer_count,
        "consumers": consumers,
        "has_template": has_template,
    }

    return render(request, "artifacts/_delete_modal.html", context)
