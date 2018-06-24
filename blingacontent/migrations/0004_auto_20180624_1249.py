# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0003_auto_20180624_1248'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gazette',
            name='published_date',
            field=models.DateField(blank=True, null=True, default=None),
        ),
        migrations.AlterField(
            model_name='gazette',
            name='slug_url',
            field=models.CharField(max_length=200, blank=True, null=True),
        ),
    ]
