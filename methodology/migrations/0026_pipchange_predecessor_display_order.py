"""Add activity_predecessor PIP support and Activity display_order on ALTER."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology", "0025_add_reference_architecture_artifact_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="pipchange",
            name="display_order",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="ALTER Activity: new execution order within workflow (1-based).",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="pipchange",
            name="relationship_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("skill_activity", "Skill → Activity"),
                    ("rule_activity", "Rule → Activity"),
                    ("agent_activity", "Agent → Activity"),
                    ("activity_workflow", "Activity → Workflow"),
                    ("artifact_activity", "Artifact → Activity"),
                    ("activity_predecessor", "Predecessor → Activity"),
                ],
                default="",
                max_length=32,
            ),
        ),
    ]
