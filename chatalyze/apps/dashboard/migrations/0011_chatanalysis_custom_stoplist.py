# Generated by Django 4.0.6 on 2022-07-20 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0010_sharelink"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatanalysis",
            name="custom_stoplist",
            field=models.JSONField(default=list),
        ),
    ]