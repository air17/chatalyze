# Generated by Django 4.0.5 on 2022-06-21 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0005_alter_chatanalysis_telegram_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatanalysis",
            name="error_text",
            field=models.TextField(blank=True),
        ),
    ]
