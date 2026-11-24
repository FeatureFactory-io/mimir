"""Admin configuration for methodology models."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected as django_delete_selected
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router, transaction
from django.db.models import Q

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    ArtifactInput,
    JoinRequest,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Team,
    TeamMembership,
    TeamPlaybook,
    Workflow,
)
from methodology.services.pip_admin_service import DECIDED_STATUSES, PIPAdminService

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse
    from django.template.response import TemplateResponse

logger = logging.getLogger(__name__)


@admin.register(Playbook)
class PlaybookAdmin(admin.ModelAdmin):
    """Admin configuration for Playbook model."""

    list_display = ('name', 'author', 'category', 'status', 'source', 'version', 'created_at')
    list_filter = ('status', 'category', 'source', 'visibility')
    search_fields = ('name', 'description', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('revert_released_playbooks_to_draft',)

    @admin.action(description="Revert Released → Draft (keeps numeric version)")
    def revert_released_playbooks_to_draft(self, request, queryset):
        from methodology.services.playbook_service import PlaybookService

        for playbook in queryset:
            try:
                PlaybookService.revert_released_playbook_to_draft(
                    playbook.pk,
                    actor=request.user,
                    reason=f"Admin revert (user id={request.user.pk}, playbook id={playbook.pk})",
                )
            except (ValidationError, PermissionError) as exc:
                self.message_user(request, f"{playbook.name}: {exc}", level=messages.ERROR)
            else:
                self.message_user(
                    request, f'Reverted "{playbook.name}" to draft.', level=messages.SUCCESS
                )


@admin.register(PlaybookVersion)
class PlaybookVersionAdmin(admin.ModelAdmin):
    """Admin configuration for PlaybookVersion model."""

    list_display = (
        "playbook",
        "version_number",
        "is_major",
        "source",
        "pip",
        "created_at",
    )
    list_filter = ("is_major", "source", "created_at")
    search_fields = ("playbook__name", "change_summary", "description")
    readonly_fields = ("created_at",)
    raw_id_fields = ("pip",)


def _pip_admin_exc_text(exc: ValidationError | Exception) -> str:
    """Render admin action errors cleanly."""
    if isinstance(exc, ValidationError):
        msg_dict = getattr(exc, "message_dict", None)
        if msg_dict:
            return str(msg_dict)
        msgs = getattr(exc, "messages", None)
        if msgs:
            return "; ".join(str(m) for m in msgs)
    return str(exc)


_PIP_DECIDED_NOTICE = "This PIP has already been decided and cannot be modified."


def _is_decided(obj: ProcessImprovementProposal | PipChange | None) -> bool:
    """Check the persisted parent state of an admin object when one is present.

    :param obj: Object from the Django Admin lookup. Example: Change 7.
    :return: Whether the object's proposal is decided. Example: True for Accepted.
    """
    proposal = obj.pip if isinstance(obj, PipChange) else obj
    return proposal is not None and proposal.status in DECIDED_STATUSES


class PipChangeInlineForm(forms.ModelForm):
    """Custom form for PipChange inline to make admin_note compact."""

    class Meta:
        model = PipChange
        fields = "__all__"
        widgets = {
            "admin_note": forms.Textarea(
                attrs={
                    "rows": 2,
                    "cols": 30,
                    "placeholder": "accepted — fits strategy; rejected — conflicts with…",
                }
            ),
        }


class PipChangeInline(admin.TabularInline):
    """Inline editor for structured PIP deltas."""

    model = PipChange
    form = PipChangeInlineForm
    extra = 0
    show_change_link = True
    fields = (
        "change_type",
        "entity_type",
        "name",
        "target_id",
        "target_name_snapshot",
        "content",
        "galdr_recommendation",
        "galdr_reasoning",
        "admin_decision",
        "admin_note",
        "order",
        "internal_ref",
        "relationship_type",
        "source_entity_type",
        "source_entity_ref",
        "target_entity_type",
        "target_entity_ref",
        "parent_workflow",
        "parent_workflow_ref",
        "insert_after_activity",
        "insert_after_activity_ref",
        "phase_ref",
        "produced_by_activity_ref",
        "artifact_type",
        "artifact_is_required",
        "append_to_playbook_end",
        "created_at",
        "updated_at",
    )

    def get_readonly_fields(
        self, request: HttpRequest, obj: ProcessImprovementProposal | None = None
    ) -> tuple[str, ...]:
        """Choose editable inline fields from the proposal's review stage.

        :param request: Admin request. Example: GET the parent form.
        :param obj: Parent proposal, if saved. Example: PIP 42 in Reviewed.
        :return: Read-only field names. Example: every field when decided.
        """
        audit_always = frozenset(
            {
                "galdr_recommendation",
                "galdr_reasoning",
                "created_at",
                "updated_at",
            }
        )
        field_names = [f.name for f in PipChange._meta.fields if not f.primary_key]
        if obj is None:
            return tuple(sorted(audit_always))
        if obj.status == ProcessImprovementProposal.STATUS_REVIEWED:
            return tuple(
                n for n in field_names if n not in {"admin_decision", "admin_note"}
            )
        if _is_decided(obj):
            return tuple(field_names)
        return tuple(sorted(audit_always))


class _PipAdmin(admin.ModelAdmin):
    """Share the proposal decision boundary between registered admin forms."""

    actions = ("delete_selected",)

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ProcessImprovementProposal | PipChange | None = None,
    ) -> bool:
        """Allow authorized edits to a proposal that has not been decided.

        :param request: Admin request. Example: POST a reviewed change.
        :param obj: Object being edited or None for model-level permission.
        :return: True when Django grants permission and the object is mutable.
        """
        return super().has_change_permission(request, obj) and not _is_decided(obj)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ProcessImprovementProposal | PipChange | None = None,
    ) -> bool:
        """Preserve decided records in direct and cascading admin delete checks.

        :param request: Admin request. Example: GET a deletion confirmation.
        :param obj: Object being deleted or None for model-level permission.
        :return: True when Django grants permission and the object is mutable.
        """
        return super().has_delete_permission(request, obj) and not _is_decided(obj)

    def render_change_form(
        self,
        request: HttpRequest,
        context: dict[str, object],
        add: bool = False,
        change: bool = False,
        form_url: str = "",
        obj: ProcessImprovementProposal | PipChange | None = None,
    ) -> TemplateResponse:
        """Explain why the registered Django form is read-only after decision.

        :param request: Admin request. Example: GET an accepted PIP's child.
        :param context: Existing Django form context.
        :param add: Whether this is the add form.
        :param change: Whether this is the change form.
        :param form_url: Optional form action URL.
        :param obj: Existing proposal or change shown in the form, if any.
        :return: Standard Django Admin form response with a notice when decided.
        """
        if _is_decided(obj):
            self.message_user(request, _PIP_DECIDED_NOTICE, messages.WARNING)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def changeform_view(
        self,
        request: HttpRequest,
        object_id: str | None = None,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        """Use Django's normal form handling under the parent lock for POSTs.

        :param request: Admin request. Example: POST a child decision.
        :param object_id: Django Admin object ID, or None for an add form.
        :param form_url: Optional form action URL.
        :param extra_context: Optional template values supplied by a caller.
        :return: Normal Django view, validation, or save response.
        :raises PermissionDenied: If the source or destination is decided.
        """
        if request.method == "POST":
            adding = object_id is None or "_saveasnew" in request.POST
            can_post = (
                self.has_add_permission(request)
                if adding
                else self.has_change_permission(request)
            )
            if not can_post:
                raise PermissionDenied
            with transaction.atomic(using=router.db_for_write(self.model)):
                self._lock_editable_proposals(
                    request,
                    self._object_selection(request, object_id),
                    self._destination_id(request),
                )
                return super().changeform_view(
                    request, object_id, form_url, extra_context
                )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def delete_view(
        self,
        request: HttpRequest,
        object_id: str,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        """Protect a confirmed direct deletion with the proposal review lock.

        :param request: Admin request. Example: confirmed POST to delete a child.
        :param object_id: Django Admin object ID.
        :param extra_context: Optional template values supplied by a caller.
        :return: Standard Django deletion or confirmation response.
        :raises PermissionDenied: If the proposal has been decided.
        """
        if request.method == "POST":
            if not self.has_delete_permission(request):
                raise PermissionDenied
            with transaction.atomic(using=router.db_for_write(self.model)):
                self._lock_editable_proposals(
                    request, self._object_selection(request, object_id)
                )
                return super().delete_view(request, object_id, extra_context)
        return super().delete_view(request, object_id, extra_context)

    @admin.action(
        permissions=["delete"], description="Delete selected %(verbose_name_plural)s"
    )
    def delete_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[ProcessImprovementProposal | PipChange],
    ) -> TemplateResponse | None:
        """Keep Django's bulk delete workflow with the same parent lock on confirm.

        :param request: Admin action request. Example: confirmed deletion POST.
        :param queryset: Existing Admin selection. Example: two pending changes.
        :return: Standard Django confirmation, or None after deleting.
        :raises PermissionDenied: If the selection includes a decided proposal.
        """
        if request.POST.get("post"):
            # Use the same identities for locking and deleting even when the
            # filtered changelist gains a row between these operations.
            selected_ids = tuple(queryset.values_list("pk", flat=True))
            selected = self.get_queryset(request).filter(pk__in=selected_ids)
            with transaction.atomic(using=router.db_for_write(self.model)):
                self._lock_editable_proposals(request, selected)
                return django_delete_selected(self, request, selected)
        return django_delete_selected(self, request, queryset)

    def _object_selection(
        self, request: HttpRequest, object_id: str | None
    ) -> QuerySet[ProcessImprovementProposal | PipChange]:
        """Resolve the form identity without reading before the review lock."""
        queryset = self.get_queryset(request)
        if object_id is None:
            return queryset.none()
        try:
            return queryset.filter(pk=unquote(object_id))
        except (ValueError, ValidationError):
            return queryset.none()

    def _destination_id(self, request: HttpRequest) -> int | None:
        """Read the posted child foreign key, leaving validation to Django's form."""
        if self.model is not PipChange:
            return None
        try:
            return int(request.POST.get("pip", ""))
        except ValueError:
            return None

    def _lock_editable_proposals(
        self,
        request: HttpRequest,
        selected: QuerySet[ProcessImprovementProposal | PipChange],
        destination_id: int | None = None,
    ) -> None:
        """Check current parent rows and reject mutations of decided proposals."""
        child_selection = self.model is PipChange
        matching = Q(pk__in=selected.values("pip_id" if child_selection else "pk"))
        if destination_id is not None:
            matching |= Q(pk=destination_id)
        proposals = ProcessImprovementProposal.objects.using(
            router.db_for_write(self.model)
        )
        locked = PIPAdminService.lock_proposals(proposals.filter(matching))
        for proposal in locked:
            if _is_decided(proposal):
                logger.info(
                    "PIP admin mutation denied | actor_id=%s pip_id=%s correlation_id=pip_review:%s reason=decided",
                    request.user.pk,
                    proposal.pk,
                    proposal.pk,
                )
                raise PermissionDenied(_PIP_DECIDED_NOTICE)
        if (
            child_selection
            and selected.exclude(pip_id__in=[pip.pk for pip in locked]).exists()
        ):
            # The child was moved while this request acquired its parent locks.
            raise PermissionDenied(
                "The change moved to another proposal. Open it again."
            )


@admin.register(ProcessImprovementProposal)
class ProcessImprovementProposalAdmin(_PipAdmin):
    inlines = (PipChangeInline,)
    list_display = (
        "title",
        "playbook",
        "status",
        "created_by",
        "change_count_column",
        "submitted_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "playbook__name", "summary")
    readonly_fields = (
        "created_at",
        "updated_at",
        "status_changed_at",
    )
    raw_id_fields = ("playbook", "created_by")
    actions = ("finalize_reviewed_pips", "delete_selected")

    @admin.action(
        description="Finalize reviewed PIPs (apply accepted changes + notify)"
    )
    def finalize_reviewed_pips(self, request, queryset):
        """Admin queue action — thin wrapper around :class:`PIPAdminService`."""

        ok = skipped = failed = 0
        for row in queryset.iterator():
            if row.status != ProcessImprovementProposal.STATUS_REVIEWED:
                skipped += 1
                continue
            try:
                PIPAdminService.finalize_pip(row, request.user)
                ok += 1
                self.message_user(
                    request,
                    f'Finalised "{row.title}" (PIP-{row.pk}).',
                    level=messages.SUCCESS,
                )
            except ValidationError as exc:
                failed += 1
                self.message_user(
                    request,
                    f"PIP-{row.pk}: {_pip_admin_exc_text(exc)}",
                    level=messages.ERROR,
                )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} proposal(s) not in Reviewed state.",
                level=messages.WARNING,
            )
        if ok == 0 and failed == 0 and not skipped:
            self.message_user(request, "No proposals selected.", level=messages.WARNING)

    @staticmethod
    def change_count_column(obj):
        return obj.changes.count()

    change_count_column.short_description = "Changes"


@admin.register(PipChange)
class PipChangeAdmin(_PipAdmin):
    list_display = ("id", "pip", "change_type", "entity_type", "order", "name")
    list_filter = ("change_type", "entity_type")
    raw_id_fields = ("pip", "parent_workflow", "insert_after_activity")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for Workflow model."""
    list_display = ('name', 'playbook', 'order', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description', 'playbook__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('playbook', 'order')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Admin configuration for Activity model."""
    list_display = ('name', 'workflow', 'phase', 'order', 'predecessor', 'successor')
    list_filter = ('phase', 'created_at')
    search_fields = ('name', 'guidance', 'workflow__name', 'workflow__playbook__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('workflow', 'order')
    filter_horizontal = ('rules',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('workflow', 'name', 'guidance')
        }),
        ('Organization', {
            'fields': ('order', 'phase')
        }),
        ('Dependencies', {
            'fields': ('predecessor', 'successor')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    """Admin configuration for Artifact model."""
    list_display = ('name', 'type', 'produced_by', 'playbook', 'is_required', 'created_at')
    list_filter = ('type', 'is_required', 'playbook')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ArtifactInput)
class ArtifactInputAdmin(admin.ModelAdmin):
    """Admin configuration for ArtifactInput model."""
    list_display = ('artifact', 'activity', 'is_required', 'created_at')
    list_filter = ('is_required',)
    search_fields = ('artifact__name', 'activity__name')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin configuration for Skill model."""
    list_display = ('title', 'playbook', 'capability_domain', 'technology_stack', 'created_at')
    search_fields = ('title', 'content', 'capability_domain', 'technology_stack')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('playbook',)


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    """Admin configuration for Rule model."""
    list_display = ('title', 'slug', 'playbook', 'always_apply', 'created_at')
    search_fields = ('title', 'slug', 'content')
    list_filter = ('always_apply', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('playbook',)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin configuration for Agent model."""
    list_display = ('name', 'playbook', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'playbook__name')
    list_filter = ('created_at', 'playbook')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('playbook',)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin configuration for Team model."""

    list_display = ["name", "visibility", "join_policy", "category", "admin", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["visibility", "category", "join_policy"]
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for TeamMembership model."""

    list_display = ["team", "user", "role", "joined_at"]
    list_filter = ["role"]
    readonly_fields = ("joined_at",)


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    """Admin configuration for JoinRequest model."""

    list_display = ["team", "user", "source", "status", "requested_at"]
    list_filter = ["status", "source"]
    readonly_fields = ("requested_at",)


@admin.register(TeamPlaybook)
class TeamPlaybookAdmin(admin.ModelAdmin):
    """Admin configuration for TeamPlaybook model."""

    list_display = ["team", "playbook", "added_by", "added_at"]
    readonly_fields = ("added_at",)
