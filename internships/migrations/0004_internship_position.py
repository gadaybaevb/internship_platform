# Generated by Django 5.1.1 on 2024-10-09 04:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0003_alter_position_stages_count"),
        ("internships", "0003_internship"),
    ]

    operations = [
        migrations.AddField(
            model_name="internship",
            name="position",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="departments.position",
            ),
        ),
    ]
