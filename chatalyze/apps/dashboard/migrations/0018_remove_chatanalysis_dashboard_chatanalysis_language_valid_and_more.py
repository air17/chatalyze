# Generated by Django 4.0.6 on 2022-09-05 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0017_remove_chatanalysis_dashboard_chatanalysis_language_valid_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="chatanalysis",
            name="dashboard_chatanalysis_language_valid",
        ),
        migrations.AlterField(
            model_name="chatanalysis",
            name="language",
            field=models.CharField(
                choices=[("ENG", "English"), ("RUS", "Russian"), ("UKR", "Ukrainian"), ("U+R", "Ukrainian+Russian")],
                default="RUS",
                max_length=3,
            ),
        ),
        migrations.AddConstraint(
            model_name="chatanalysis",
            constraint=models.CheckConstraint(
                check=models.Q(("language__in", ("ENG", "RUS", "UKR", "U+R"))),
                name="dashboard_chatanalysis_language_valid",
            ),
        ),
    ]
