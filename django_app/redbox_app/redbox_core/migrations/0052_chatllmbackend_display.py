# Generated by Django 5.1.1 on 2024-10-11 12:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('redbox_core', '0051_alter_user_accessibility_description_alter_user_role_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatllmbackend',
            name='display',
            field=models.CharField(blank=True, help_text='name to display in UI.', max_length=128, null=True),
        ),
    ]
