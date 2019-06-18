# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tagging.fields


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0010_auto_20181107_0941'),
    ]

    operations = [
        migrations.AddField(
            model_name='gazette',
            name='tags',
            field=tagging.fields.TagField(max_length=255, blank=True),
        ),
    ]
