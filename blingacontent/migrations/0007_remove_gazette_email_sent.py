# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0006_gazette_use_markdown'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gazette',
            name='email_sent',
        ),
    ]
