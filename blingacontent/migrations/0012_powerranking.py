# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0026_auto_20250117_1229'),
        ('blingacontent', '0011_gazette_tags'),
    ]

    operations = [
        migrations.CreateModel(
            name='PowerRanking',
            fields=[
                ('year', models.IntegerField(primary_key=True, serialize=False)),
                ('ranking_1', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_1_finishes', to='blingaleague.Member')),
                ('ranking_10', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_10_finishes', to='blingaleague.Member')),
                ('ranking_11', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_11_finishes', to='blingaleague.Member')),
                ('ranking_12', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_12_finishes', to='blingaleague.Member')),
                ('ranking_13', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_13_finishes', to='blingaleague.Member')),
                ('ranking_14', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_14_finishes', to='blingaleague.Member')),
                ('ranking_2', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_2_finishes', to='blingaleague.Member')),
                ('ranking_3', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_3_finishes', to='blingaleague.Member')),
                ('ranking_4', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_4_finishes', to='blingaleague.Member')),
                ('ranking_5', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_5_finishes', to='blingaleague.Member')),
                ('ranking_6', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_6_finishes', to='blingaleague.Member')),
                ('ranking_7', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_7_finishes', to='blingaleague.Member')),
                ('ranking_8', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_8_finishes', to='blingaleague.Member')),
                ('ranking_9', models.ForeignKey(blank=True, null=True, default=None, related_name='power_ranking_9_finishes', to='blingaleague.Member')),
            ],
            options={
                'ordering': ['-year'],
            },
        ),
    ]
