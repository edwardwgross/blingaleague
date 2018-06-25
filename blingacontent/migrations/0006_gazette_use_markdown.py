# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0005_auto_20180624_1910'),
    ]

    operations = [
        migrations.AddField(
            model_name='gazette',
            name='use_markdown',
            field=models.BooleanField(default=True),
        ),
    ]
