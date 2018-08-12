# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0008_gazette_publish_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='gazette',
            name='email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
