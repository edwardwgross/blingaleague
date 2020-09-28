# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0017_keeper'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='keeper',
            options={'ordering': ['year', 'round', 'team', 'name']},
        ),
        migrations.AddField(
            model_name='keeper',
            name='position',
            field=models.CharField(max_length=10, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tradedasset',
            name='position',
            field=models.CharField(max_length=10, blank=True, null=True),
        ),
    ]
