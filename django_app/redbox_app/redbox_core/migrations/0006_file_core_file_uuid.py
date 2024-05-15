import uuid

from django.db import migrations, models


def set_core_file_uuid_defaults(apps, schema_editor):
    File = apps.get_model('redbox_core', 'File')
    for file in File.objects.all().iterator():
        file.core_file_uuid = uuid.uuid4()
        file.save()

def reverse_set_core_file_uuid_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('redbox_core', '0005_alter_user_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='core_file_uuid',
            field=models.UUIDField(null=True),
            preserve_default=False,
        ),
        migrations.RunPython(set_core_file_uuid_defaults, reverse_set_core_file_uuid_defaults),
        migrations.AlterField(
            model_name='file',
            name='core_file_uuid',
            field=models.UUIDField(unique=True, null=False),
        ),
    ]
