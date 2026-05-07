"""Migration: Add mfa_enabled field to users table.

The User model defines mfa_enabled but the initial migration omitted it.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='mfa_enabled',
            field=models.BooleanField(
                default=False,
                help_text='When True, login requires a second factor via MFAHook.',
            ),
        ),
    ]