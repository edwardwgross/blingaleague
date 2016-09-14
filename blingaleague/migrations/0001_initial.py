# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.IntegerField()),
                ('week', models.IntegerField()),
                ('winner_score', models.DecimalField(max_digits=6, decimal_places=2)),
                ('loser_score', models.DecimalField(max_digits=6, decimal_places=2)),
                ('notes', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('nickname', models.CharField(max_length=50, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='game',
            name='loser',
            field=models.ForeignKey(related_name=b'games_lost', to='blingaleague.Member'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='game',
            name='winner',
            field=models.ForeignKey(related_name=b'games_won', to='blingaleague.Member'),
            preserve_default=True,
        ),
    ]
