"""Workflow Service - Business logic for workflow operations."""

import logging
from typing import Optional, List
from django.db import transaction, models
from django.core.exceptions import ValidationError
from methodology.models import Activity, ActivityWorkflowMembership, Workflow
from methodology.services.playbook_service import PlaybookService

logger = logging.getLogger(__name__)

_ABBREVIATION_MIN_LEN = 2
_ABBREVIATION_MAX_LEN = 8


def _normalize_abbreviation(value: Optional[str]) -> Optional[str]:
    """
    Uppercase and validate an explicit workflow code.

    :param value: Raw abbreviation or None. Example: "ida"
    :return: Normalized code, empty string, or None if omitted. Example: "IDA"
    :raises ValidationError: if the value is not 2–8 letters
    """
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    if not cleaned:
        return ""
    if not cleaned.isalpha() or not (
        _ABBREVIATION_MIN_LEN <= len(cleaned) <= _ABBREVIATION_MAX_LEN
    ):
        raise ValidationError(
            f"abbreviation must be {_ABBREVIATION_MIN_LEN}–{_ABBREVIATION_MAX_LEN} letters"
        )
    return cleaned


def _assert_unique_abbreviation(playbook, abbreviation: str, exclude_id=None) -> None:
    """
    Reject an explicit code already used in the playbook.

    :param playbook: Parent playbook
    :param abbreviation: Normalized code. Example: "IDA"
    :param exclude_id: Workflow pk to ignore on update. Example: 85
    :raises ValidationError: if another workflow already uses the code
    """
    qs = Workflow.objects.filter(playbook=playbook, abbreviation=abbreviation)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError(
            f"Abbreviation '{abbreviation}' already exists in this playbook"
        )


class WorkflowService:
    """Service class for workflow operations."""
    
    @staticmethod
    def create_workflow(playbook, name, description='', order=None, abbreviation=None):
        """
        Create workflow with validation, auto-order, and optional explicit code.

        :param playbook: Parent playbook
        :param name: Workflow name. Example: "IDA Demand Assessment"
        :param description: Optional description
        :param order: Optional 1-based position; defaults to max+1
        :param abbreviation: Optional 2–8 letter code. Example: "IDA"
        :return: Created Workflow
        :raises ValidationError: on duplicate name or abbreviation
        """
        logger.info(f"Creating workflow '{name}' in playbook {playbook.pk}")
        
        # Check for duplicate name
        if Workflow.objects.filter(playbook=playbook, name=name).exists():
            raise ValidationError(f"Workflow '{name}' already exists in this playbook")

        normalized_abbr = _normalize_abbreviation(abbreviation)
        if normalized_abbr:
            _assert_unique_abbreviation(playbook, normalized_abbr)
        
        # Auto-assign order if not provided (lock siblings to avoid concurrent max+1 races)
        with transaction.atomic():
            if order is None:
                locked = Workflow.objects.select_for_update().filter(playbook=playbook)
                max_order = locked.aggregate(max_order=models.Max('order'))['max_order']
                order = (max_order or 0) + 1

            create_kwargs = {
                "name": name,
                "description": description,
                "playbook": playbook,
                "order": order,
            }
            if normalized_abbr:
                create_kwargs["abbreviation"] = normalized_abbr
            workflow = Workflow.objects.create(**create_kwargs)
        
        logger.info(
            "Workflow '%s' created with ID %s, order %s, abbreviation %s",
            name,
            workflow.pk,
            workflow.order,
            workflow.abbreviation,
        )
        return workflow
    
    @staticmethod
    def get_workflow(workflow_id):
        """Get workflow by ID."""
        logger.info(f"Retrieving workflow {workflow_id}")
        return Workflow.objects.get(pk=workflow_id)
    
    @staticmethod
    def get_workflows_for_playbook(playbook_id):
        """Get all workflows for playbook, ordered."""
        logger.info(f"Retrieving workflows for playbook {playbook_id}")
        return list(Workflow.objects.filter(playbook_id=playbook_id).order_by('order', 'created_at'))
    
    @staticmethod
    def list_global_workflows(user):
        """
        Get all workflows from playbooks accessible to user (owned + public + team).
        
        :param user: User whose accessible workflows to retrieve.
        :returns: QuerySet of Workflow instances ordered by playbook name and workflow order.
        """
        logger.info(f"Retrieving global workflows for user {user.id}")
        accessible_playbook_ids = PlaybookService.get_accessible_playbook_ids(user)
        workflows = Workflow.objects.filter(
            playbook_id__in=accessible_playbook_ids
        ).select_related('playbook').order_by('playbook__name', 'order')
        
        logger.info(f"User {user.id} has access to {workflows.count()} workflows")
        return workflows

    @staticmethod
    def list_global_workflows_for_guest():
        """Delegate to guest browse service (released public playbooks only)."""
        from methodology.services.guest_browse_service import list_global_workflows_for_guest

        return list_global_workflows_for_guest()
    
    @staticmethod
    @transaction.atomic
    def update_workflow(workflow_id, **data):
        """Update workflow with validation."""
        logger.info(f"Updating workflow {workflow_id}")
        
        workflow = Workflow.objects.get(pk=workflow_id)
        
        # Check for duplicate name if changing name
        if 'name' in data and data['name'] != workflow.name:
            if Workflow.objects.filter(playbook=workflow.playbook, name=data['name']).exists():
                raise ValidationError(f"Workflow '{data['name']}' already exists in this playbook")

        if "abbreviation" in data:
            normalized_abbr = _normalize_abbreviation(data["abbreviation"])
            if normalized_abbr:
                _assert_unique_abbreviation(
                    workflow.playbook, normalized_abbr, exclude_id=workflow.pk
                )
            data["abbreviation"] = normalized_abbr or ""
            logger.info(
                "Workflow %s abbreviation %s → %s",
                workflow_id,
                workflow.abbreviation,
                data["abbreviation"] or "(auto)",
            )
        
        previous_order = workflow.order
        # Update fields
        for field, value in data.items():
            setattr(workflow, field, value)

        workflow.save()
        if "order" in data and data["order"] != previous_order:
            logger.info(
                "Workflow %s order changed %s → %s playbook=%s",
                workflow_id,
                previous_order,
                workflow.order,
                workflow.playbook_id,
            )
        else:
            logger.info(f"Workflow {workflow_id} updated")
        return workflow
    
    @staticmethod
    @transaction.atomic
    def delete_workflow(workflow_id):
        """Delete workflow."""
        logger.info(f"Deleting workflow {workflow_id}")
        workflow = Workflow.objects.get(pk=workflow_id)
        workflow.delete()
        logger.info(f"Workflow {workflow_id} deleted")
    
    @staticmethod
    @transaction.atomic
    def duplicate_workflow(workflow_id, new_name):
        """Duplicate workflow (shallow copy)."""
        logger.info(f"Duplicating workflow {workflow_id} as '{new_name}'")
        
        original = Workflow.objects.get(pk=workflow_id)
        
        # Check for duplicate name
        if Workflow.objects.filter(playbook=original.playbook, name=new_name).exists():
            raise ValidationError(f"Workflow '{new_name}' already exists in this playbook")
        
        # Get next order
        max_order = Workflow.objects.filter(playbook=original.playbook).aggregate(
            max_order=models.Max('order')
        )['max_order']
        next_order = (max_order or 0) + 1
        
        # Create duplicate
        duplicate = Workflow.objects.create(
            name=new_name,
            description=original.description,
            playbook=original.playbook,
            order=next_order
        )
        
        logger.info(f"Workflow duplicated as {duplicate.pk}")
        return duplicate

    @staticmethod
    @transaction.atomic
    def add_activity_to_workflow(activity_id: int, workflow_id: int, order: Optional[int] = None):
        """
        Cross-list an activity in a secondary workflow via ActivityWorkflowMembership.

        Primary home remains ``Activity.workflow`` FK.
        """
        activity = Activity.objects.select_related("workflow__playbook").get(pk=activity_id)
        workflow = Workflow.objects.select_related("playbook").get(pk=workflow_id)
        if activity.workflow.playbook_id != workflow.playbook_id:
            raise ValidationError("Activity and workflow must belong to the same playbook.")
        if activity.workflow_id == workflow_id:
            raise ValidationError("Activity already has this workflow as its primary home.")
        if ActivityWorkflowMembership.objects.filter(
            activity_id=activity_id,
            workflow_id=workflow_id,
        ).exists():
            logger.info(
                "Activity %s already cross-listed in workflow %s — no-op",
                activity_id,
                workflow_id,
            )
            return ActivityWorkflowMembership.objects.get(
                activity_id=activity_id,
                workflow_id=workflow_id,
            )
        if order is None:
            agg = ActivityWorkflowMembership.objects.filter(workflow_id=workflow_id).aggregate(
                max_order=models.Max("order"),
            )
            order = int(agg["max_order"] or 0) + 1
        membership = ActivityWorkflowMembership.objects.create(
            activity=activity,
            workflow=workflow,
            order=order,
            is_primary=False,
        )
        logger.info(
            "Cross-listed activity %s '%s' into workflow %s order=%s",
            activity_id,
            activity.name,
            workflow_id,
            order,
        )
        return membership

    @staticmethod
    @transaction.atomic
    def remove_activity_from_workflow(activity_id: int, workflow_id: int):
        """Remove secondary workflow membership (not the primary Activity.workflow FK)."""
        activity = Activity.objects.get(pk=activity_id)
        if activity.workflow_id == workflow_id:
            raise ValidationError(
                "Cannot remove primary workflow membership — use activity move out of scope."
            )
        deleted, _ = ActivityWorkflowMembership.objects.filter(
            activity_id=activity_id,
            workflow_id=workflow_id,
        ).delete()
        if deleted:
            logger.info(
                "Removed cross-list activity %s from workflow %s",
                activity_id,
                workflow_id,
            )
        else:
            logger.info(
                "No membership for activity %s in workflow %s — no-op",
                activity_id,
                workflow_id,
            )

    @staticmethod
    def get_workflow_for_user(workflow_id, user, *, write: bool = False, prefetch_activities: bool = False):
        """
        Load workflow and enforce playbook access: ``can_view`` for reads, owner for writes.

        :param workflow_id: Workflow primary key
        :param user: Django user
        :param write: When True, require playbook author == user
        :param prefetch_activities: When True, prefetch ``activities`` for read tooling
        :returns: Workflow instance
        :raises Workflow.DoesNotExist: If workflow row is missing
        :raises PermissionError: If read access denied
        :raises Playbook.DoesNotExist: If write path and playbook not owned
        """
        qs = Workflow.objects.select_related("playbook")
        if prefetch_activities:
            qs = qs.prefetch_related("activities")
        workflow = qs.get(pk=workflow_id)
        if write:
            PlaybookService.get_owned_playbook(workflow.playbook_id, user)
        else:
            PlaybookService.get_playbook(workflow.playbook_id, user)
        return workflow
