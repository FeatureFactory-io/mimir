"""User Journey Certification Test for NAV-06 Global Search."""
import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import expect

from methodology.models import Activity, Playbook, Workflow

User = get_user_model()


@pytest.fixture
def nav06_sample_data(transactional_db):
    """Same searchable sample as tests/integration/test_global_search.py (NAV-06)."""
    user = User.objects.create_user(
        username='nav06_user',
        email='nav06@example.com',
        password='testpass123',
    )
    playbook = Playbook.objects.create(
        name='Component Development Playbook',
        description='Playbook for components',
        category='development',
        author=user,
    )
    workflow = Workflow.objects.create(
        playbook=playbook,
        name='Component Workflow',
        description='Workflow for components',
        order=1,
    )
    Activity.objects.create(
        workflow=workflow,
        name='Create Component',
        guidance='Do component work',
        order=1,
    )
    return {
        'username': 'nav06_user',
        'password': 'testpass123',
        'playbook_name': 'Component Development Playbook',
    }


@pytest.mark.e2e
def test_complete_global_search_journey(page, live_server, nav06_sample_data):
    """Test complete global search journey with HTMX."""
    # Login
    page.goto(f'{live_server.url}/auth/user/login/')
    page.get_by_test_id('login-username-input').fill(nav06_sample_data['username'])
    page.get_by_test_id('login-password-input').fill(nav06_sample_data['password'])
    page.get_by_test_id('login-submit-button').click()
    expect(page).to_have_url(f'{live_server.url}/dashboard/')
    
    # Verify navbar search visible
    search_input = page.get_by_test_id('global-search-input')
    expect(search_input).to_be_visible()
    
    # Type in search (HTMX listens for keyup, not programmatic fill alone)
    search_input.fill('Component')
    search_input.dispatch_event('keyup')
    expect(page.get_by_test_id('global-search-suggestions')).to_be_visible(timeout=10_000)
    
    # Submit search
    search_input.press('Enter')
    expect(page).to_have_url(f'{live_server.url}/search/?q=Component')
    
    # Verify results page summary and content
    expect(page.get_by_test_id('global-search-summary')).to_be_visible()
    expect(page.locator('body')).to_contain_text(nav06_sample_data['playbook_name'])


@pytest.mark.e2e
def test_anonymous_user_no_search(page, live_server):
    """Test anonymous user cannot see search."""
    page.goto(f'{live_server.url}/')
    search_form = page.locator('[data-testid="global-search-form"]')
    expect(search_form).not_to_be_visible()
