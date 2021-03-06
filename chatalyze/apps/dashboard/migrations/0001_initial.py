# Generated by Django 4.0.5 on 2022-06-16 22:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chat_file", models.FileField(upload_to="chatfiles")),
                ("chat_name", models.CharField(default="-", max_length=255)),
                ("chat_platform", models.CharField(default="-", max_length=255)),
                ("messages_count", models.IntegerField(default=0)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("READY", "Ready"), ("PROCESSING", "Processing"), ("ERROR", "Error")],
                        default="PROCESSING",
                        max_length=10,
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-updated"],
            },
        ),
        migrations.AddConstraint(
            model_name="chatanalysis",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ["READY", "PROCESSING", "ERROR"])),
                name="dashboard_chatanalysis_status_valid",
            ),
        ),
    ]
