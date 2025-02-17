# Generated by Django 5.1.1 on 2024-10-08 10:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0003_alter_position_stages_count"),
        ("internships", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Material",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                (
                    "file",
                    models.FileField(blank=True, null=True, upload_to="materials/"),
                ),
                ("stage", models.IntegerField()),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="departments.position",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="InternshipStage",
        ),
    ]
