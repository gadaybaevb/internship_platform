# Generated by Django 5.1.1 on 2024-10-08 09:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="position",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="departments.position",
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="departments.department",
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrator"),
                    ("mentor", "Mentor"),
                    ("intern", "Intern"),
                ],
                default="intern",
                max_length=10,
            ),
        ),
    ]
