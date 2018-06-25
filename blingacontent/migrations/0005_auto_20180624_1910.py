# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0004_auto_20180624_1249'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gazette',
            old_name='slug_url',
            new_name='slug',
        ),
        migrations.AddField(
            model_name='gazette',
            name='email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
