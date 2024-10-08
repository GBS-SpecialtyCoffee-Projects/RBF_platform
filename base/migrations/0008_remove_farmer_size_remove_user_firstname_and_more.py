# Generated by Django 4.1 on 2024-08-12 16:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0007_farmer_profile_completed_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="farmer",
            name="size",
        ),
        migrations.RemoveField(
            model_name="user",
            name="firstname",
        ),
        migrations.RemoveField(
            model_name="user",
            name="is_active",
        ),
        migrations.RemoveField(
            model_name="user",
            name="lastname",
        ),
        migrations.RemoveField(
            model_name="user",
            name="middlename",
        ),
        migrations.RemoveField(
            model_name="user",
            name="phone_number",
        ),
        migrations.AddField(
            model_name="farmer",
            name="annual_production",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="cultivars",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="cup_scores_received",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="farm_size",
            field=models.CharField(default=False, max_length=255),
        ),
        migrations.AddField(
            model_name="farmer",
            name="firstname",
            field=models.CharField(default=False, max_length=255),
        ),
        migrations.AddField(
            model_name="farmer",
            name="harvest_season",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="lastname",
            field=models.CharField(default=False, max_length=255),
        ),
        migrations.AddField(
            model_name="farmer",
            name="main_role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("owner", "Owner"),
                    ("manager", "Manager"),
                    ("worker", "Worker"),
                ],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="farmer",
            name="middlename",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="phone_number",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="preferred_communication_method",
            field=models.CharField(
                blank=True,
                choices=[("whatsapp", "WhatsApp"), ("email", "Email")],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="farmer",
            name="processing_description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="processing_method",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="profile_picture",
            field=models.ImageField(
                blank=True, null=True, upload_to="farmer_profiles/"
            ),
        ),
        migrations.AddField(
            model_name="farmer",
            name="quality_report_link",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="farmer",
            name="source_of_cup_scores",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="roasterphoto",
            name="profile",
            field=models.ImageField(
                blank=True, null=True, upload_to="roaster_profiles/"
            ),
        ),
        migrations.AlterField(
            model_name="farmer",
            name="bio",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="farmer",
            name="farm_name",
            field=models.CharField(default=False, max_length=255),
        ),
        migrations.AlterField(
            model_name="farmer",
            name="location",
            field=models.CharField(default=False, max_length=255),
        ),
        migrations.AlterField(
            model_name="farmerphoto",
            name="order",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="farmerphoto",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="farmer_photos/"),
        ),
        migrations.AlterField(
            model_name="user",
            name="password",
            field=models.CharField(max_length=128, verbose_name="password"),
        ),
    ]
