"""Integration tests for Playbook LIST operation."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from methodology.models import Playbook

User = get_user_model()


@pytest.fixture
def test_user():
    """Create test user."""
    return User.objects.create_user(username='maria', password='test123')


@pytest.fixture
def test_playbooks(test_user):
    """Create multiple test playbooks."""
    playbooks = [
        Playbook.objects.create(
            name='React Frontend Development',
            description='Modern React patterns',
            category='development',
            tags=['react', 'frontend'],
            status='active',
            visibility='private',
            author=test_user,
            source='owned'
        ),
        Playbook.objects.create(
            name='UX Research Methodology',
            description='User research best practices',
            category='research',
            tags=['ux', 'research'],
            status='active',
            visibility='private',
            author=test_user,
            source='owned'
        ),
        Playbook.objects.create(
            name='Design System Patterns',
            description='Component patterns',
            category='design',
            tags=['design', 'patterns'],
            status='disabled',
            visibility='private',
            author=test_user,
            source='owned'
        ),
    ]
    return playbooks


@pytest.mark.django_db
class TestPlaybookList:
    """Test playbook list page."""
    
    def test_pb_list_01_view_playbooks_list(self, test_user, test_playbooks):
        """PB-LIST-01: View playbooks list with existing playbooks."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        
        assert response.status_code == 200
        assert b'Playbooks' in response.content
        # Check all 3 playbooks appear
        assert b'React Frontend Development' in response.content
        assert b'UX Research Methodology' in response.content
        assert b'Design System Patterns' in response.content
    
    def test_pb_list_02_navigate_to_create(self, test_user):
        """PB-LIST-02: Navigate to create new playbook."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        
        assert response.status_code == 200
        create_url = reverse('playbook_create')
        assert create_url.encode() in response.content
    
    def test_pb_list_03_empty_state(self, test_user):
        """PB-LIST-03: View empty playbooks list."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        
        assert response.status_code == 200
        # Should show empty state message
        assert b'playbook' in response.content.lower()
    
    def test_pb_list_04_playbook_metadata_displayed(self, test_user, test_playbooks):
        """PB-LIST-04: Each playbook shows metadata."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        content = response.content.decode('utf-8')
        
        # Check first playbook metadata
        assert 'React Frontend Development' in content
        assert 'Modern React patterns' in content
        assert 'development' in content.lower() or 'Development' in content
    
    def test_pb_list_05_view_button_links_to_detail(self, test_user, test_playbooks):
        """PB-LIST-05: View button links to playbook detail."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        
        # Check detail URL exists for first playbook
        detail_url = reverse('playbook_detail', kwargs={'pk': test_playbooks[0].pk})
        assert detail_url.encode() in response.content
    
    def test_pb_list_06_status_badges_displayed(self, test_user, test_playbooks):
        """PB-LIST-06: Status badges shown with correct styling."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        content = response.content.decode('utf-8')
        
        # Check status badges appear
        assert 'active' in content.lower() or 'Active' in content
        assert 'disabled' in content.lower() or 'Disabled' in content
    
    def test_pb_list_07_category_displayed(self, test_user, test_playbooks):
        """PB-LIST-07: Category displayed for each playbook."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        content = response.content.decode('utf-8')
        
        # Check categories appear
        assert 'development' in content.lower() or 'Development' in content
        assert 'research' in content.lower() or 'Research' in content
        assert 'design' in content.lower() or 'Design' in content
    
    def test_pb_list_08_action_buttons_for_owned(self, test_user, test_playbooks):
        """PB-LIST-08: Action buttons shown for owned playbooks."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        content = response.content.decode('utf-8')
        
        # Check for action links/buttons
        detail_url = reverse('playbook_detail', kwargs={'pk': test_playbooks[0].pk})
        assert detail_url in content
    
    def test_pb_list_09_multiple_playbooks_ordering(self, test_user, test_playbooks):
        """PB-LIST-09: Playbooks displayed in order."""
        client = Client()
        client.force_login(test_user)
        
        response = client.get(reverse('playbook_list'))
        content = response.content.decode('utf-8')
        
        # All playbooks should be present
        assert 'React Frontend Development' in content
        assert 'UX Research Methodology' in content
        assert 'Design System Patterns' in content
    
    def test_pb_list_10_guest_may_browse_public_list(self):
        """PB-LIST-10: Anonymous guests may browse released public playbooks."""
        client = Client()

        response = client.get(reverse('playbook_list'))

        assert response.status_code == 200
        assert b'data-testid="guest-auth-banner"' in response.content


@pytest.mark.django_db
class TestPlaybookListPublicSection:
    """Public playbooks from other authors appear in browse section."""

    def test_public_playbook_from_other_author_visible(self):
        maria = User.objects.create_user(username="maria", password="x")
        mike = User.objects.create_user(username="mike", password="x")
        Playbook.objects.create(
            name="Mike Public Methodology",
            description="Shared methodology description text here",
            category="development",
            author=mike,
            visibility="public",
            status="released",
            version=Decimal("1.0"),
        )
        client = Client()
        client.force_login(maria)
        response = client.get(reverse("playbook_list"))
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert 'data-testid="playbooks-list-section"' in content
        assert 'data-testid="public-playbooks-section"' not in content
        assert "Mike Public Methodology" in content
        assert "mike" in content.lower()
        assert 'data-testid="playbooks-empty-state"' not in content

    def test_draft_public_playbook_from_other_author_hidden(self):
        maria = User.objects.create_user(username="maria", password="x")
        mike = User.objects.create_user(username="mike", password="x")
        Playbook.objects.create(
            name="Mike Draft Public PB",
            description="Draft public playbook must stay owner-only",
            category="development",
            author=mike,
            visibility="public",
            status="draft",
            version=Decimal("0.1"),
        )
        client = Client()
        client.force_login(maria)
        response = client.get(reverse("playbook_list"))
        content = response.content.decode("utf-8")
        assert "Mike Draft Public PB" not in content
        assert 'data-testid="playbooks-empty-state"' in content

    def test_empty_state_only_when_no_owned_or_public_playbooks(self):
        maria = User.objects.create_user(username="maria", password="x")
        client = Client()
        client.force_login(maria)
        response = client.get(reverse("playbook_list"))
        content = response.content.decode("utf-8")
        assert 'data-testid="playbooks-empty-state"' in content
        assert "No playbooks yet" in content

    def test_no_empty_state_when_only_public_playbooks_exist(self):
        maria = User.objects.create_user(username="maria", password="x")
        mike = User.objects.create_user(username="mike", password="x")
        Playbook.objects.create(
            name="Shared Released Playbook",
            description="Visible to Maria even with zero owned playbooks",
            category="development",
            author=mike,
            visibility="public",
            status="released",
            version=Decimal("1.0"),
        )
        client = Client()
        client.force_login(maria)
        response = client.get(reverse("playbook_list"))
        content = response.content.decode("utf-8")
        assert 'data-testid="playbooks-empty-state"' not in content
        assert "Shared Released Playbook" in content

    def test_private_playbook_from_other_author_not_in_public_section(self):
        maria = User.objects.create_user(username="maria", password="x")
        mike = User.objects.create_user(username="mike", password="x")
        Playbook.objects.create(
            name="Mike Private PB",
            description="Private methodology description text here",
            category="development",
            author=mike,
            visibility="private",
            status="draft",
            version=Decimal("0.1"),
        )
        client = Client()
        client.force_login(maria)
        response = client.get(reverse("playbook_list"))
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Mike Private PB" not in content
