# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0023_auto_20221001_1151'),
    ]

    operations = [
        migrations.CreateModel(
            name='FutureGame',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('year', models.IntegerField(db_index=True)),
                ('week', models.IntegerField(db_index=True)),
                ('team_1', models.ForeignKey(related_name='future_games_team_1', to='blingaleague.Member')),
                ('team_2', models.ForeignKey(related_name='future_games_team_2', to='blingaleague.Member')),
            ],
            bases=(models.Model, blingaleague.models.AbstractGame),
        ),
    ]
