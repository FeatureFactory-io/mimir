"""
Integration tests for team playbook items appearing in global lists.

Tests that workflows, activities, phases, and artifacts from team playbooks
appear in their respective global list views for team members.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from methodology.models import Playbook, Workflow, Activity, Phase, Artifact, Skill, Rule, Team, TeamMembership, TeamPlaybook
from django.test import Client

User = get_user_model()


@pytest.mark.django_db
class TestTeamGlobalLists:
    """Test that team playbook items appear in global lists for team members."""

    def test_workflow_global_list_includes_team_playbooks(self):
        """Team members should see workflows from team playbooks in global list."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        
        # Admin creates a playbook
        playbook = Playbook.objects.create(
            name="Team Methodology",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private"
        )
        
        # Admin creates a workflow
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Team Workflow",
            description="Shared workflow",
            order=1
        )
        
        # Admin creates a team and shares the playbook
        team = Team.objects.create(name="Dev Team Workflows", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act - dp2580 views workflow global list
        client = Client()
        client.force_login(dp2580)
        response = client.get('/workflows/')
        
        # Assert
        assert response.status_code == 200
        workflows = response.context['workflows']
        workflow_ids = [w.id for w in workflows]
        assert workflow.id in workflow_ids, "Team workflow should appear in global list"

    def test_activity_global_list_includes_team_playbooks(self):
        """Team members should see activities from team playbooks in global list."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        
        playbook = Playbook.objects.create(
            name="Team Methodology",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private"
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Team Workflow",
            description="Shared workflow",
            order=1
        )
        
        activity = Activity.objects.create(
            workflow=workflow,
            name="Team Activity",
            guidance="Team guidance",
            order=1
        )
        
        team = Team.objects.create(name="Dev Team Activities", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act
        client = Client()
        client.force_login(dp2580)
        response = client.get('/activities/')
        
        # Assert
        assert response.status_code == 200
        activities = response.context['activities']
        activity_ids = [a.id for a in activities]
        assert activity.id in activity_ids, "Team activity should appear in global list"

    def test_phase_global_list_includes_team_playbooks(self):
        """Team members should see phases from team playbooks in global list."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        
        playbook = Playbook.objects.create(
            name="Team Methodology",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private"
        )
        
        phase = Phase.objects.create(
            playbook=playbook,
            name="Team Phase",
            description="Team phase description",
            order=1
        )
        
        team = Team.objects.create(name="Dev Team Phases", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act
        client = Client()
        client.force_login(dp2580)
        response = client.get('/phases/')
        
        # Assert
        assert response.status_code == 200
        phases = response.context['phases']
        phase_ids = [p.id for p in phases]
        assert phase.id in phase_ids, "Team phase should appear in global list"

    def test_artifact_global_list_includes_team_playbooks(self):
        """Team members should see artifacts from team playbooks in global list."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        
        playbook = Playbook.objects.create(
            name="Team Methodology",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private"
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Team Workflow",
            description="Shared workflow",
            order=1
        )
        
        activity = Activity.objects.create(
            workflow=workflow,
            name="Team Activity",
            guidance="Team guidance",
            order=1
        )
        
        artifact = Artifact.objects.create(
            playbook=playbook,
            name="Team Artifact",
            description="Team artifact description",
            type="Document",
            produced_by=activity
        )
        
        team = Team.objects.create(name="Dev Team Artifacts", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act
        client = Client()
        client.force_login(dp2580)
        response = client.get('/artifacts/')
        
        # Assert
        assert response.status_code == 200
        artifacts = response.context['artifacts']
        artifact_ids = [a.id for a in artifacts]
        assert artifact.id in artifact_ids, "Team artifact should appear in global list"

    def test_non_member_cannot_see_private_team_workflows(self):
        """Non-members should not see workflows from private team playbooks."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        
        # Create another user who is NOT a team member
        other_user, _ = User.objects.get_or_create(username="other_user_wf", defaults={"email": "other@test.com"})
        
        playbook = Playbook.objects.create(
            name="Team Methodology",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private"  # Private!
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Team Workflow",
            description="Shared workflow",
            order=1
        )
        
        team = Team.objects.create(name="Dev Team Private", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act - other_user (not a team member) views workflow global list
        client = Client()
        client.force_login(other_user)
        response = client.get('/workflows/')
        
        # Assert
        assert response.status_code == 200
        workflows = response.context['workflows']
        workflow_ids = [w.id for w in workflows]
        assert workflow.id not in workflow_ids, "Private team workflow should NOT appear for non-members"

    def test_non_member_cannot_see_private_team_artifacts(self):
        """Non-members should not see artifacts from private team playbooks."""
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        other_user, _ = User.objects.get_or_create(username="other_user_art", defaults={"email": "other3@test.com"})

        playbook = Playbook.objects.create(
            name="Team Methodology Art",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private",
        )

        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Team Workflow",
            description="Shared workflow",
            order=1,
        )

        activity = Activity.objects.create(
            workflow=workflow,
            name="Team Activity",
            guidance="Team guidance",
            order=1,
        )

        artifact = Artifact.objects.create(
            playbook=playbook,
            name="Team Artifact Private",
            description="Team artifact description",
            type="Document",
            produced_by=activity,
        )

        team = Team.objects.create(name="Dev Team Art Private", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamPlaybook.objects.create(team=team, playbook=playbook)

        client = Client()
        client.force_login(other_user)
        response = client.get('/artifacts/')

        assert response.status_code == 200
        artifact_ids = [a.id for a in response.context['artifacts']]
        assert artifact.id not in artifact_ids

    def test_non_member_cannot_see_private_team_phases(self):
        """Non-members should not see phases from private team playbooks."""
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        other_user, _ = User.objects.get_or_create(username="other_user_ph", defaults={"email": "other4@test.com"})

        playbook = Playbook.objects.create(
            name="Team Methodology Phase",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private",
        )

        phase = Phase.objects.create(
            playbook=playbook,
            name="Team Phase Private",
            description="Team phase description",
            order=1,
        )

        team = Team.objects.create(name="Dev Team Phase Private", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamPlaybook.objects.create(team=team, playbook=playbook)

        client = Client()
        client.force_login(other_user)
        response = client.get('/phases/')

        assert response.status_code == 200
        phase_ids = [p.id for p in response.context['phases']]
        assert phase.id not in phase_ids

    def test_public_team_playbook_items_visible_to_all(self):
        """Public team playbook items should be visible to all authenticated users."""
        # Arrange
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})
        other_user, _ = User.objects.get_or_create(username="other_user_pub", defaults={"email": "other2@test.com"})
        
        playbook = Playbook.objects.create(
            name="Public Team Methodology",
            description="Public shared methodology",
            author=admin,
            status="released",
            visibility="public"  # Public!
        )
        
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Public Team Workflow",
            description="Public shared workflow",
            order=1
        )
        
        team = Team.objects.create(name="Public Team Items", visibility=Team.VISIBILITY_PUBLIC, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)
        
        # Act - other_user (not a team member) views workflow global list
        client = Client()
        client.force_login(other_user)
        response = client.get('/workflows/')
        
        # Assert
        assert response.status_code == 200
        workflows = response.context['workflows']
        workflow_ids = [w.id for w in workflows]
        assert workflow.id in workflow_ids, "Public team workflow should appear for all users"

    def test_team_member_can_view_skill_detail(self):
        """Team members should open skill detail for team-shared playbooks."""
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})

        playbook = Playbook.objects.create(
            name="Team Methodology Skills",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private",
        )
        skill = Skill.objects.create(
            playbook=playbook,
            title="Team Skill",
            content="Team skill content",
        )

        team = Team.objects.create(name="Dev Team Skills", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)

        client = Client()
        client.force_login(dp2580)
        url = reverse("skill_detail", kwargs={"playbook_pk": playbook.pk, "skill_pk": skill.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert skill.title.encode() in response.content

    def test_team_member_can_view_rule_detail(self):
        """Team members should open rule detail for team-shared playbooks."""
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        dp2580, _ = User.objects.get_or_create(username="dp2580", defaults={"email": "dp2580@test.com"})

        playbook = Playbook.objects.create(
            name="Team Methodology Rules",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private",
        )
        rule = Rule.objects.create(
            playbook=playbook,
            title="Team Rule",
            slug="team-rule",
            content="Team rule content",
        )

        team = Team.objects.create(name="Dev Team Rules", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamMembership.objects.create(team=team, user=dp2580, role="member")
        TeamPlaybook.objects.create(team=team, playbook=playbook)

        client = Client()
        client.force_login(dp2580)
        url = reverse("rule_detail", kwargs={"playbook_pk": playbook.pk, "rule_pk": rule.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert rule.title.encode() in response.content

    def test_non_member_cannot_view_team_skill_detail(self):
        """Non-members should not access skill detail on private team playbooks."""
        admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@test.com"})
        other_user, _ = User.objects.get_or_create(
            username="other_user_skill",
            defaults={"email": "other_skill@test.com"},
        )

        playbook = Playbook.objects.create(
            name="Team Methodology Skill Private",
            description="Shared methodology",
            author=admin,
            status="released",
            visibility="private",
        )
        skill = Skill.objects.create(
            playbook=playbook,
            title="Private Team Skill",
            content="Private skill content",
        )

        team = Team.objects.create(name="Dev Team Skill Private", visibility=Team.VISIBILITY_HIDDEN, admin=admin)
        TeamMembership.objects.create(team=team, user=admin, role="admin")
        TeamPlaybook.objects.create(team=team, playbook=playbook)

        client = Client()
        client.force_login(other_user)
        url = reverse("skill_detail", kwargs={"playbook_pk": playbook.pk, "skill_pk": skill.pk})
        response = client.get(url)

        assert response.status_code == 404
