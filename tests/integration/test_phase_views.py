"""
Integration tests for Phase views.

Tests the complete phase CRUD workflow via Django test client.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from methodology.models import Playbook, Phase, Workflow, Activity

User = get_user_model()


@pytest.mark.django_db
class TestPhaseDetailView:
    """Test phase_detail view."""
    
    def test_phase_detail_renders_correctly(self, client):
        """Phase detail page renders with correct phase data."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Inception',
            description='Initial phase',
            order=1
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name='Test Workflow',
            description='Test workflow',
            order=1
        )
        
        activity = Activity.objects.create(
            workflow=workflow,
            name='Test Activity',
            guidance='Test guidance',
            order=1,
            phase=phase
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'phase' in response.context
        assert response.context['phase'].name == 'Inception'
        assert response.context['phase'].description == 'Initial phase'
        assert response.context['phase'].order == 1
        
        # Check activities are in context
        assert 'workflow_activities' in response.context
        assert 'artifacts' in response.context
        
        # Check template content
        content = response.content.decode()
        assert 'Inception' in content
        assert 'Initial phase' in content
        assert 'Test Activity' in content
        assert 'Test Workflow' in content
    
    def test_phase_detail_with_no_activities(self, client):
        """Phase detail page renders correctly when phase has no activities."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Empty Phase',
            description='No activities yet',
            order=1
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert response.context['phase'].name == 'Empty Phase'
        content = response.content.decode()
        assert 'No activities assigned to this phase yet' in content
    
    def test_phase_detail_edit_button_visible_for_draft(self, client):
        """Edit button is visible when playbook is draft."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Test Phase',
            description='Test',
            order=1
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        content = response.content.decode()
        assert 'data-testid="edit-button"' in content
        assert 'data-testid="delete-button"' in content
    
    def test_phase_detail_no_edit_button_for_released(self, client):
        """Edit button is NOT visible when playbook is released."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='released'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Test Phase',
            description='Test',
            order=1
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        content = response.content.decode()
        assert 'data-testid="edit-button"' not in content
        assert 'data-testid="delete-button"' not in content
    
    def test_phase_detail_anonymous_returns_404_for_private_playbook(self, client):
        """Phase detail returns 404 for anonymous users on non-guest-readable playbooks."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Test Phase',
            description='Test',
            order=1
        )
        
        # Execute (not logged in)
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert — guest read allowed but private draft playbook is not visible
        assert response.status_code == 404

    def test_phase_detail_anonymous_public_released_returns_200(self, client):
        """Guest can view phase detail on released public playbook."""
        from decimal import Decimal

        user = User.objects.create_user(username='pubowner', password='testpass123')
        playbook = Playbook.objects.create(
            name='Public Released PB',
            description='Guest readable',
            category='development',
            author=user,
            visibility='public',
            status='released',
            version=Decimal('1.0'),
        )
        phase = Phase.objects.create(
            playbook=playbook,
            name='Guest Phase',
            description='Test',
            order=1,
        )
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert b'Guest Phase' in response.content
        assert b'data-testid="edit-button"' not in response.content
    
    def test_phase_detail_permission_denied_for_other_user(self, client):
        """Phase detail returns 404 when user doesn't own the playbook."""
        # Setup
        owner = User.objects.create_user(username='owner', password='testpass123')
        other_user = User.objects.create_user(username='other', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=owner,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Test Phase',
            description='Test',
            order=1
        )
        
        # Execute (logged in as other_user)
        client.login(username='other', password='testpass123')
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 404


@pytest.mark.django_db
class TestPhaseListView:
    """Test phase_list view (playbook-scoped)."""
    
    def test_phase_list_renders_all_phases(self, client):
        """Phase list shows all phases for a playbook."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test Description',
            category='development',
            author=user,
            status='draft'
        )
        
        phase1 = Phase.objects.create(
            playbook=playbook,
            name='Inception',
            description='Phase 1',
            order=1
        )
        
        phase2 = Phase.objects.create(
            playbook=playbook,
            name='Elaboration',
            description='Phase 2',
            order=2
        )
        
        # Execute
        url = reverse('phase_list', kwargs={'playbook_pk': playbook.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'phases' in response.context
        phases = list(response.context['phases'])
        assert len(phases) == 2
        assert phases[0].name == 'Inception'
        assert phases[1].name == 'Elaboration'
        
        content = response.content.decode()
        assert 'Inception' in content
        assert 'Elaboration' in content


@pytest.mark.django_db
class TestPhaseGlobalListView:
    """Test phase_list_global view."""
    
    def test_global_list_shows_all_user_phases(self, client):
        """Global phase list shows all phases across all user's playbooks."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook1 = Playbook.objects.create(
            name='Playbook 1',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        playbook2 = Playbook.objects.create(
            name='Playbook 2',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        Phase.objects.create(playbook=playbook1, name='Phase A', order=1)
        Phase.objects.create(playbook=playbook1, name='Phase B', order=2)
        Phase.objects.create(playbook=playbook2, name='Phase C', order=1)
        
        # Execute
        url = reverse('phase_list_global')
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'phases' in response.context
        phases = list(response.context['phases'])
        assert len(phases) == 3
        
        content = response.content.decode()
        assert 'Phase A' in content
        assert 'Phase B' in content
        assert 'Phase C' in content
    
    def test_global_list_search_filters_by_name(self, client):
        """Global phase list search filters by phase name."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        Phase.objects.create(playbook=playbook, name='Inception', order=1)
        Phase.objects.create(playbook=playbook, name='Elaboration', order=2)
        Phase.objects.create(playbook=playbook, name='Construction', order=3)
        
        # Execute
        url = reverse('phase_list_global') + '?q=Inception'
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        phases = list(response.context['phases'])
        assert len(phases) == 1
        assert phases[0].name == 'Inception'


@pytest.mark.django_db
class TestPhaseCreateView:
    """Test phase_create view."""
    
    def test_create_phase_success(self, client):
        """Creating a phase succeeds with valid data."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        # Execute
        url = reverse('phase_create', kwargs={'playbook_pk': playbook.pk})
        response = client.post(url, {
            'name': 'New Phase',
            'description': 'Test phase description',
            'order': '1'
        })
        
        # Assert
        assert response.status_code == 302  # Redirect on success
        assert Phase.objects.filter(playbook=playbook, name='New Phase').exists()
        
        phase = Phase.objects.get(playbook=playbook, name='New Phase')
        assert phase.description == 'Test phase description'
        assert phase.order == 1
    
    def test_create_phase_auto_order(self, client):
        """Creating a phase without order auto-assigns next order."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        Phase.objects.create(playbook=playbook, name='Phase 1', order=1)
        Phase.objects.create(playbook=playbook, name='Phase 2', order=2)
        
        # Execute
        url = reverse('phase_create', kwargs={'playbook_pk': playbook.pk})
        response = client.post(url, {
            'name': 'Phase 3',
            'description': 'Auto-ordered phase'
        })
        
        # Assert
        assert response.status_code == 302
        phase = Phase.objects.get(playbook=playbook, name='Phase 3')
        assert phase.order == 3  # Auto-assigned next order
    
    def test_create_phase_duplicate_name_fails(self, client):
        """Creating a phase with duplicate name fails."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        Phase.objects.create(playbook=playbook, name='Inception', order=1)
        
        # Execute
        url = reverse('phase_create', kwargs={'playbook_pk': playbook.pk})
        response = client.post(url, {
            'name': 'Inception',
            'description': 'Duplicate name'
        })
        
        # Assert
        assert response.status_code == 200  # Stays on form
        assert Phase.objects.filter(playbook=playbook, name='Inception').count() == 1
    
    def test_create_phase_released_playbook_fails(self, client):
        """Creating a phase in released playbook fails."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='released'
        )
        
        # Execute
        url = reverse('phase_create', kwargs={'playbook_pk': playbook.pk})
        response = client.post(url, {
            'name': 'New Phase',
            'description': 'Should fail'
        })
        
        # Assert
        assert response.status_code == 302  # Redirect with error
        assert not Phase.objects.filter(playbook=playbook, name='New Phase').exists()


@pytest.mark.django_db
class TestPhaseEditView:
    """Test phase_edit view."""
    
    def test_edit_phase_success(self, client):
        """Editing a phase succeeds with valid data."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Old Name',
            description='Old description',
            order=1
        )
        
        # Execute
        url = reverse('phase_edit', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.post(url, {
            'name': 'New Name',
            'description': 'New description',
            'order': '2'
        })
        
        # Assert
        assert response.status_code == 302  # Redirect on success
        phase.refresh_from_db()
        assert phase.name == 'New Name'
        assert phase.description == 'New description'
        assert phase.order == 2
    
    def test_edit_phase_released_playbook_fails(self, client):
        """Editing a phase in released playbook fails."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='released'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Original Name',
            description='Original',
            order=1
        )
        
        # Execute
        url = reverse('phase_edit', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.post(url, {
            'name': 'Should Not Change',
            'description': 'Should not change'
        })
        
        # Assert
        assert response.status_code == 302  # Redirect with error
        phase.refresh_from_db()
        assert phase.name == 'Original Name'  # Unchanged


@pytest.mark.django_db
class TestPhaseDeleteView:
    """Test phase_delete view."""
    
    def test_delete_phase_success(self, client):
        """Deleting a phase succeeds."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='To Delete',
            description='Will be deleted',
            order=1
        )
        
        phase_pk = phase.pk
        
        # Execute
        url = reverse('phase_delete', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.post(url)
        
        # Assert
        assert response.status_code == 302  # Redirect on success
        assert not Phase.objects.filter(pk=phase_pk).exists()
    
    def test_delete_phase_with_activities_fails(self, client):
        """Deleting a phase with assigned activities fails with validation error."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Cannot Delete',
            order=1
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name='Test Workflow',
            order=1
        )
        
        activity = Activity.objects.create(
            workflow=workflow,
            name='Test Activity',
            order=1,
            phase=phase
        )
        
        # Execute
        url = reverse('phase_delete', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.post(url)
        
        # Assert - deletion fails, phase still exists
        assert response.status_code == 302  # Redirect with error
        assert Phase.objects.filter(pk=phase.pk).exists()
        activity.refresh_from_db()
        assert activity.phase == phase  # Phase reference unchanged
    
    def test_delete_phase_released_playbook_fails(self, client):
        """Deleting a phase in released playbook fails."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='released'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Cannot Delete',
            order=1
        )
        
        # Execute
        url = reverse('phase_delete', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.post(url)
        
        # Assert
        assert response.status_code == 302  # Redirect with error
        assert Phase.objects.filter(pk=phase.pk).exists()  # Still exists


@pytest.mark.django_db
class TestPhaseActivityWiring:
    """Test phase-activity relationships and wiring."""
    
    def test_activity_can_be_assigned_to_phase(self, client):
        """Activity can be assigned to a phase via update."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Inception',
            order=1
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name='Test Workflow',
            order=1
        )
        
        activity = Activity.objects.create(
            workflow=workflow,
            name='Test Activity',
            order=1
        )
        
        # Execute - update activity to assign phase
        url = reverse('activity_edit', kwargs={
            'playbook_pk': playbook.pk,
            'workflow_pk': workflow.pk,
            'activity_pk': activity.pk
        })
        response = client.post(url, {
            'name': 'Test Activity',
            'guidance': 'Test guidance',
            'phase': phase.pk,
            'order': '1'
        })
        
        # Assert
        assert response.status_code == 302
        activity.refresh_from_db()
        assert activity.phase == phase
    
    def test_phase_detail_shows_assigned_activities(self, client):
        """Phase detail page shows all activities assigned to that phase."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Inception',
            order=1
        )
        
        workflow1 = Workflow.objects.create(
            playbook=playbook,
            name='Workflow 1',
            order=1
        )
        
        workflow2 = Workflow.objects.create(
            playbook=playbook,
            name='Workflow 2',
            order=2
        )
        
        # Create activities in different workflows, same phase
        activity1 = Activity.objects.create(
            workflow=workflow1,
            name='Activity 1',
            order=1,
            phase=phase
        )
        
        activity2 = Activity.objects.create(
            workflow=workflow1,
            name='Activity 2',
            order=2,
            phase=phase
        )
        
        activity3 = Activity.objects.create(
            workflow=workflow2,
            name='Activity 3',
            order=1,
            phase=phase
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        
        # All activities should be visible
        assert 'Activity 1' in content
        assert 'Activity 2' in content
        assert 'Activity 3' in content
        
        # Both workflows should be shown
        assert 'Workflow 1' in content
        assert 'Workflow 2' in content
        
        # Activity count should be correct
        assert phase.get_activity_count() == 3
    
    def test_phase_detail_groups_activities_by_workflow(self, client):
        """Phase detail groups activities by their parent workflow."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Construction',
            order=1
        )
        
        workflow1 = Workflow.objects.create(
            playbook=playbook,
            name='Backend',
            order=1
        )
        
        workflow2 = Workflow.objects.create(
            playbook=playbook,
            name='Frontend',
            order=2
        )
        
        # Backend activities
        Activity.objects.create(workflow=workflow1, name='Setup DB', order=1, phase=phase)
        Activity.objects.create(workflow=workflow1, name='Create Models', order=2, phase=phase)
        
        # Frontend activities
        Activity.objects.create(workflow=workflow2, name='Setup React', order=1, phase=phase)
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'workflow_activities' in response.context
        
        workflow_activities = response.context['workflow_activities']
        assert len(workflow_activities) == 2
        
        # Check grouping
        backend_group = next(w for w in workflow_activities if w['workflow'].name == 'Backend')
        assert len(backend_group['activities']) == 2
        
        frontend_group = next(w for w in workflow_activities if w['workflow'].name == 'Frontend')
        assert len(frontend_group['activities']) == 1
    
    def test_activity_without_phase_not_shown_in_phase_detail(self, client):
        """Activities without phase assignment don't appear in phase detail."""
        # Setup
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.login(username='testuser', password='testpass123')
        
        playbook = Playbook.objects.create(
            name='Test Playbook',
            description='Test',
            category='development',
            author=user,
            status='draft'
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name='Inception',
            order=1
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name='Test Workflow',
            order=1
        )
        
        # Activity with phase
        Activity.objects.create(
            workflow=workflow,
            name='Assigned Activity',
            order=1,
            phase=phase
        )
        
        # Activity without phase
        Activity.objects.create(
            workflow=workflow,
            name='Unassigned Activity',
            order=2,
            phase=None
        )
        
        # Execute
        url = reverse('phase_detail', kwargs={'playbook_pk': playbook.pk, 'phase_pk': phase.pk})
        response = client.get(url)
        
        # Assert
        content = response.content.decode()
        assert 'Assigned Activity' in content
        assert 'Unassigned Activity' not in content
