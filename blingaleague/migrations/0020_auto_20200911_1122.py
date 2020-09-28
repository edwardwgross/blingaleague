# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0019_auto_20200911_1121'),
    ]

    operations = [
        migrations.AlterField(
            model_name='keeper',
            name='position',
            field=models.CharField(max_length=10, choices=[('QB', 'QB'), ('RB', 'RB'), ('WR', 'WR'), ('TE', 'TE'), ('DEF', 'DEF'), ('K', 'K')]),
        ),
    ]
