# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0005_auto_20160915_1924'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='defunct',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
