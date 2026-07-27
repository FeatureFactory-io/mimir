"""
Integration tests for Artifact global LIST+FIND operation.

Tests global artifact list display, search, and navigation.
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from methodology.models import Artifact, Playbook, Workflow, Activity

User = get_user_model()


@pytest.mark.django_db
class TestArtifactListGlobal:
    """Integration tests for global artifact list functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data for each test."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='maria_artifact_global',
            email='maria_artifact@test.com',
            password='testpass123'
        )
        self.client.login(username='maria_artifact_global', password='testpass123')

        self.playbook = Playbook.objects.create(
            name='React Frontend v1.2',
            description='React methodology',
            category='development',
            status='draft',
            source='owned',
            author=self.user
        )
        
        self.workflow = Workflow.objects.create(
            playbook=self.playbook,
            name='Build Feature',
            order=1
        )
        
        self.activity = Activity.objects.create(
            workflow=self.workflow,
            name='Implement Backend',
            order=1
        )

    def test_global_list_page_loads(self):
        """Global artifacts list page loads successfully."""
        Artifact.objects.create(
            playbook=self.playbook,
            produced_by=self.activity,
            name='API Spec'
        )
        url = reverse('artifact_list_global')
        response = self.client.get(url)

        assert response.status_code == 200
        assert b'Artifacts' in response.content

    def test_shows_artifacts_table(self):
        """Artifacts table shows artifacts with key columns."""
        Artifact.objects.create(
            playbook=self.playbook,
            produced_by=self.activity,
            name='Database Schema',
            description='PostgreSQL schema',
            type='Code'
        )
        url = reverse('artifact_list_global')
        response = self.client.get(url)

        assert response.status_code == 200
        assert b'Database Schema' in response.content
        assert b'data-testid="artifacts-table"' in response.content

    def test_search_by_name(self):
        """Search by name filters results."""
        Artifact.objects.create(
            playbook=self.playbook,
            produced_by=self.activity,
            name='API Documentation',
            description='REST API docs'
        )
        Artifact.objects.create(
            playbook=self.playbook,
            produced_by=self.activity,
            name='Database Schema',
            description='DB schema'
        )
        url = reverse('artifact_list_global')
        response = self.client.get(url, {'q': 'API'})

        assert response.status_code == 200
        assert b'API Documentation' in response.content
        assert b'Database Schema' not in response.content

    def test_empty_state(self):
        """Empty state shown when no artifacts exist."""
        url = reverse('artifact_list_global')
        response = self.client.get(url)

        assert response.status_code == 200
        assert b'data-testid="empty-state"' in response.content
        assert b'No artifacts yet' in response.content

    def test_anonymous_guest_can_browse_global_list(self):
        """Anonymous users can browse released public artifacts (guest read)."""
        self.client.logout()
        url = reverse('artifact_list_global')
        response = self.client.get(url)

        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content
        assert b'data-testid="empty-state"' in response.content

    def test_shows_playbook_name(self):
        """Artifact table shows the parent playbook name."""
        Artifact.objects.create(
            playbook=self.playbook,
            produced_by=self.activity,
            name='Test Artifact',
            description='Test'
        )
        url = reverse('artifact_list_global')
        response = self.client.get(url)

        assert response.status_code == 200
        assert b'React Frontend v1.2' in response.content
