# Generated by Django 5.1.1 on 2024-10-09 05:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_delete_internship"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="full_name",
            field=models.CharField(default=2, max_length=255),
            preserve_default=False,
        ),
    ]
