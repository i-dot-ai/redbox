# Custom generated migration will need to be amended for contribution back to i.ai

import redbox_app.redbox_core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("redbox_core", "0070_alter_user_options_alter_user_managers_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.EmailField(
                max_length=254, null=True
            ),
        ),
    ]
