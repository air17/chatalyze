# Generated by Django 4.0.6 on 2022-07-26 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0015_alter_chatanalysis_custom_stoplist"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatanalysis",
            name="progress_id",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]