# Generated manually for email_users AdminAction type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0002_add_health_check_conditions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminaction',
            name='action_type',
            field=models.CharField(
                choices=[
                    ('create', 'Create'),
                    ('update', 'Update'),
                    ('delete', 'Delete'),
                    ('approve', 'Approve'),
                    ('reject', 'Reject'),
                    ('archive', 'Archive'),
                    ('bulk_action', 'Bulk Action'),
                    ('email_users', 'Email Users'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
