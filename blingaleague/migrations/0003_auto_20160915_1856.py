# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0002_auto_20160913_2141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='loser_score',
            field=models.DecimalField(max_digits=6, decimal_places=2, db_index=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='week',
            field=models.IntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='winner_score',
            field=models.DecimalField(max_digits=6, decimal_places=2, db_index=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='year',
            field=models.IntegerField(db_index=True),
        ),
    ]
