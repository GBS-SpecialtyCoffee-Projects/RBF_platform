# Generated by Django 4.1 on 2024-07-07 19:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meetingrequest',
            name='farmer',
        ),
        migrations.RemoveField(
            model_name='meetingrequest',
            name='roaster',
        ),
        migrations.AddField(
            model_name='meetingrequest',
            name='requestee',
            field=models.ForeignKey(default=7, on_delete=django.db.models.deletion.CASCADE, related_name='meeting_requests_received', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='meetingrequest',
            name='requester',
            field=models.ForeignKey(default=7, on_delete=django.db.models.deletion.CASCADE, related_name='meeting_requests_made', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
