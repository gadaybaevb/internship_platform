# Generated by Django 5.1.1 on 2024-10-10 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tests", "0003_test_passing_score_alter_answer_text_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="test",
            name="time_limit",
            field=models.IntegerField(default=30),
        ),
    ]
