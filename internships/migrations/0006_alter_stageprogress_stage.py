# Generated by Django 5.1.1 on 2024-10-09 07:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internships", "0005_stageprogress"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stageprogress",
            name="stage",
            field=models.IntegerField(default=1),
        ),
    ]
