# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0003_auto_20160915_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='Season',
            fields=[
                ('year', models.IntegerField(serialize=False, primary_key=True)),
                ('place_1', models.ForeignKey(related_name=b'first_place_finishes', to='blingaleague.Member')),
                ('place_2', models.ForeignKey(related_name=b'second_place_finishes', to='blingaleague.Member')),
                ('place_3', models.ForeignKey(related_name=b'third_place_finishes', to='blingaleague.Member')),
                ('place_4', models.ForeignKey(related_name=b'fourth_place_finishes', to='blingaleague.Member')),
                ('place_5', models.ForeignKey(related_name=b'fifth_place_finishes', to='blingaleague.Member')),
                ('place_6', models.ForeignKey(related_name=b'sixth_place_finishes', to='blingaleague.Member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
