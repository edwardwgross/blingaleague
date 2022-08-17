# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0020_auto_20200911_1122'),
    ]

    operations = [
        migrations.CreateModel(
            name='DraftPick',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=200)),
                ('position', models.CharField(max_length=10, choices=[('QB', 'QB'), ('RB', 'RB'), ('WR', 'WR'), ('TE', 'TE'), ('K', 'K'), ('DEF', 'DEF')])),
                ('year', models.IntegerField(db_index=True)),
                ('round', models.IntegerField()),
                ('pick_in_round', models.IntegerField()),
                ('is_keeper', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['year', 'round', 'pick_in_round'],
            },
            bases=(models.Model, blingaleague.models.ComparableObject),
        ),
        migrations.AlterModelOptions(
            name='member',
            options={'ordering': ['nickname', 'first_name', 'last_name']},
        ),
        migrations.AlterModelOptions(
            name='trade',
            options={'ordering': ['-year', '-week', '-date', '-pk']},
        ),
        migrations.AlterModelOptions(
            name='tradedasset',
            options={'ordering': ['trade', 'receiver', 'keeper_cost', 'name', 'sender']},
        ),
        migrations.AlterField(
            model_name='keeper',
            name='position',
            field=models.CharField(max_length=10, choices=[('QB', 'QB'), ('RB', 'RB'), ('WR', 'WR'), ('TE', 'TE'), ('K', 'K'), ('DEF', 'DEF')]),
        ),
        migrations.AlterField(
            model_name='tradedasset',
            name='position',
            field=models.CharField(max_length=10, blank=True, null=True, choices=[('QB', 'QB'), ('RB', 'RB'), ('WR', 'WR'), ('TE', 'TE'), ('K', 'K'), ('DEF', 'DEF')]),
        ),
        migrations.AddField(
            model_name='draftpick',
            name='original_team',
            field=models.ForeignKey(blank=True, null=True, related_name='traded_picks', to='blingaleague.Member'),
        ),
        migrations.AddField(
            model_name='draftpick',
            name='team',
            field=models.ForeignKey(related_name='draft_picks', to='blingaleague.Member'),
        ),
    ]
