# Generated by Django 4.0.6 on 2022-07-21 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0011_chatanalysis_custom_stoplist"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatanalysis",
            name="chat_platform",
            field=models.CharField(
                choices=[("-", " "), ("Telegram", "Telegram"), ("WhatsApp", "Whatsapp"), ("Facebook", "Facebook")],
                default="-",
                max_length=25,
            ),
        ),
    ]
