# Generated by Django 4.0.5 on 2022-06-28 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0007_remove_chatanalysis_dashboard_chatanalysis_status_valid_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="chatanalysis",
            constraint=models.CheckConstraint(
                check=models.Q(("language__in", ("ENG", "RUS"))), name="dashboard_chatanalysis_language_valid"
            ),
        ),
    ]
