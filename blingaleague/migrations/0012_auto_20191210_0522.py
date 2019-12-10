# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0011_auto_20181107_0941'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('year', models.IntegerField(db_index=True)),
                ('week', models.IntegerField(db_index=True)),
                ('date', models.DateField(db_index=True, default=None)),
            ],
        ),
        migrations.CreateModel(
            name='TradedAsset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=200)),
                ('is_draft_pick', models.BooleanField(default=False)),
                ('keeper_cost', models.IntegerField(blank=True, null=True)),
                ('sender', models.ForeignKey(related_name='traded_assets', to='blingaleague.Member')),
                ('trade', models.ForeignKey(related_name='assets', to='blingaleague.Trade')),
            ],
        ),
    ]
