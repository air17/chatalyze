# Generated by Django 4.0.6 on 2022-07-23 14:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0013_chatanalysis_dashboard_chatanalysis_chat_platform_valid"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="chatanalysis",
            options={
                "ordering": ["-updated"],
                "verbose_name": "Chat Analysis",
                "verbose_name_plural": "Chat Analyses",
            },
        ),
        migrations.AlterModelOptions(
            name="sharelink",
            options={"verbose_name": "Shared Link", "verbose_name_plural": "Shared Links"},
        ),
    ]
