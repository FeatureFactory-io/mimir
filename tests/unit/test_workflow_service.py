"""Unit tests for WorkflowService."""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from methodology.models import Playbook, Workflow
from methodology.services.workflow_service import WorkflowService

User = get_user_model()


@pytest.fixture
def test_user():
    """Create test user."""
    return User.objects.create_user(username='testuser', password='test123')


@pytest.fixture
def test_playbook(test_user):
    """Create test playbook."""
    return Playbook.objects.create(
        name='Test Playbook',
        description='Test description',
        category='development',
        author=test_user,
        source='owned'
    )


@pytest.mark.django_db
class TestWorkflowService:
    """Test WorkflowService methods."""
    
    def test_create_workflow_with_all_fields(self, test_playbook):
        """Test creating workflow with all fields specified."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Component Development',
            description='Build and test components',
            order=2
        )
        
        assert workflow.name == 'Component Development'
        assert workflow.description == 'Build and test components'
        assert workflow.playbook == test_playbook
        assert workflow.order == 2
    
    def test_create_workflow_auto_order(self, test_playbook):
        """Test workflow order is auto-assigned as max + 1."""
        workflow1 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='First',
            order=1
        )
        workflow2 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Second'
            # order not specified, should be auto-assigned
        )
        
        assert workflow2.order == 2
    
    def test_create_workflow_duplicate_name_fails(self, test_playbook):
        """Test creating workflow with duplicate name raises error."""
        WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Duplicate Name',
            order=1
        )
        
        with pytest.raises(ValidationError):
            WorkflowService.create_workflow(
                playbook=test_playbook,
                name='Duplicate Name',
                order=2
            )
    
    def test_get_workflow(self, test_playbook):
        """Test retrieving workflow by ID."""
        created = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Test Workflow'
        )
        
        retrieved = WorkflowService.get_workflow(created.id)
        
        assert retrieved.id == created.id
        assert retrieved.name == 'Test Workflow'
    
    def test_get_workflow_not_found(self):
        """Test get_workflow raises DoesNotExist for invalid ID."""
        with pytest.raises(Workflow.DoesNotExist):
            WorkflowService.get_workflow(99999)
    
    def test_get_workflows_for_playbook(self, test_playbook):
        """Test retrieving all workflows for a playbook."""
        workflow1 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='First',
            order=1
        )
        workflow2 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Second',
            order=2
        )
        workflow3 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Third',
            order=3
        )
        
        workflows = WorkflowService.get_workflows_for_playbook(test_playbook.id)
        
        assert len(workflows) == 3
        assert workflows[0].name == 'First'
        assert workflows[1].name == 'Second'
        assert workflows[2].name == 'Third'
    
    def test_get_workflows_empty_playbook(self, test_playbook):
        """Test get_workflows returns empty list for playbook with no workflows."""
        workflows = WorkflowService.get_workflows_for_playbook(test_playbook.id)
        
        assert workflows == []
    
    def test_update_workflow_name(self, test_playbook):
        """Test updating workflow name."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Original Name'
        )
        
        updated = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            name='Updated Name'
        )
        
        assert updated.name == 'Updated Name'
    
    def test_update_workflow_description(self, test_playbook):
        """Test updating workflow description."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Test'
        )
        
        updated = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            description='New description'
        )
        
        assert updated.description == 'New description'
    
    def test_update_workflow_order(self, test_playbook):
        """Test updating workflow order."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Test',
            order=1
        )
        
        updated = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            order=5
        )
        
        assert updated.order == 5

    def test_create_workflow_explicit_abbreviation(self, test_playbook):
        """Issue #182: create accepts an explicit code instead of auto IAN."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Investigate the Demand Assumption',
            abbreviation='IDA',
        )
        assert workflow.abbreviation == 'IDA'

    def test_update_workflow_abbreviation(self, test_playbook):
        """Issue #182: update can correct a bad auto-generated code."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Investigate the Demand Assumption',
        )
        assert workflow.abbreviation != 'IDA'
        updated = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            abbreviation='IDA',
        )
        assert updated.abbreviation == 'IDA'

    def test_create_workflow_duplicate_abbreviation_fails(self, test_playbook):
        """Explicit abbreviation must be unique per playbook."""
        WorkflowService.create_workflow(
            playbook=test_playbook,
            name='First',
            abbreviation='IDA',
        )
        with pytest.raises(ValidationError, match='IDA'):
            WorkflowService.create_workflow(
                playbook=test_playbook,
                name='Second',
                abbreviation='IDA',
            )
    
    def test_update_workflow_duplicate_name_fails(self, test_playbook):
        """Test updating to duplicate name raises error."""
        workflow1 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='First'
        )
        workflow2 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Second'
        )
        
        with pytest.raises(ValidationError):
            WorkflowService.update_workflow(
                workflow_id=workflow2.id,
                name='First'
            )
    
    def test_delete_workflow(self, test_playbook):
        """Test deleting workflow."""
        workflow = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='To Delete'
        )
        workflow_id = workflow.id
        
        WorkflowService.delete_workflow(workflow_id)
        
        assert not Workflow.objects.filter(id=workflow_id).exists()
    
    def test_delete_workflow_not_found(self):
        """Test deleting non-existent workflow raises error."""
        with pytest.raises(Workflow.DoesNotExist):
            WorkflowService.delete_workflow(99999)
    
    def test_duplicate_workflow(self, test_playbook):
        """Test duplicating workflow creates copy."""
        original = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Original',
            description='Original description',
            order=1
        )
        
        duplicate = WorkflowService.duplicate_workflow(
            workflow_id=original.id,
            new_name='Original (Copy)'
        )
        
        assert duplicate.name == 'Original (Copy)'
        assert duplicate.description == original.description
        assert duplicate.playbook == original.playbook
        assert duplicate.order > original.order
        assert duplicate.id != original.id
    
    def test_duplicate_workflow_duplicate_name_fails(self, test_playbook):
        """Test duplicating with existing name raises error."""
        workflow1 = WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Workflow 1'
        )
        WorkflowService.create_workflow(
            playbook=test_playbook,
            name='Existing Name'
        )
        
        with pytest.raises(ValidationError):
            WorkflowService.duplicate_workflow(
                workflow_id=workflow1.id,
                new_name='Existing Name'
            )
