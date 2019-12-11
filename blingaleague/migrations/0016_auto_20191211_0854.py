# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0015_auto_20191210_1712'),
    ]

    operations = [
        migrations.CreateModel(
            name='Postseason',
            fields=[
                ('year', models.IntegerField(primary_key=True, serialize=False)),
                ('place_1', models.ForeignKey(blank=True, null=True, default=None, related_name='first_place_finishes', to='blingaleague.Member')),
                ('place_2', models.ForeignKey(blank=True, null=True, default=None, related_name='second_place_finishes', to='blingaleague.Member')),
                ('place_3', models.ForeignKey(blank=True, null=True, default=None, related_name='third_place_finishes', to='blingaleague.Member')),
                ('place_4', models.ForeignKey(blank=True, null=True, default=None, related_name='fourth_place_finishes', to='blingaleague.Member')),
                ('place_5', models.ForeignKey(blank=True, null=True, default=None, related_name='fifth_place_finishes', to='blingaleague.Member')),
                ('place_6', models.ForeignKey(blank=True, null=True, default=None, related_name='sixth_place_finishes', to='blingaleague.Member')),
            ],
            options={
                'ordering': ['-year'],
            },
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_1',
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_2',
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_3',
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_4',
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_5',
        ),
        migrations.RemoveField(
            model_name='season',
            name='place_6',
        ),
        migrations.DeleteModel(
            name='Season',
        ),
    ]
