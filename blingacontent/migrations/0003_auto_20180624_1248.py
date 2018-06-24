# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0002_gazette'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gazette',
            name='published_date',
            field=models.DateField(null=True, default=None),
        ),
    ]
