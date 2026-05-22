from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0041_alter_meetingrequest_proposed_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "farmer",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="conversations_as_farmer",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "roaster",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="conversations_as_roaster",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
                "unique_together": {("roaster", "farmer")},
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="messages",
                        to="base.conversation",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="chat_messages_sent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
