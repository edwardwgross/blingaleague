# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0007_remove_gazette_email_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='gazette',
            name='publish_flag',
            field=models.BooleanField(default=False),
        ),
    ]
