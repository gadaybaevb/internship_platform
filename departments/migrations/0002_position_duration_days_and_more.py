# Generated by Django 5.1.1 on 2024-10-08 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="position",
            name="duration_days",
            field=models.IntegerField(default=30),
        ),
        migrations.AddField(
            model_name="position",
            name="final_test_after_days",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="position",
            name="intermediate_test_after_stage",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="position",
            name="stages_count",
            field=models.IntegerField(default=5),
        ),
    ]
