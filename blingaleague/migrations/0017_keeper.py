# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0016_auto_20191211_0854'),
    ]

    operations = [
        migrations.CreateModel(
            name='Keeper',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=200)),
                ('year', models.IntegerField(db_index=True)),
                ('round', models.IntegerField()),
                ('times_kept', models.IntegerField()),
                ('team', models.ForeignKey(related_name='keepers', to='blingaleague.Member')),
            ],
            options={
                'ordering': ['name', 'year', 'round', 'team'],
            },
            bases=(models.Model, blingaleague.models.ComparableObject),
        ),
    ]
