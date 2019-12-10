# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0014_auto_20191210_1029'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tradedasset',
            options={'ordering': ['trade', 'sender', 'receiver', 'keeper_cost', 'name']},
        ),
        migrations.AddField(
            model_name='tradedasset',
            name='keeper_eligible',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='tradedasset',
            name='receiver',
            field=models.ForeignKey(related_name='assets_received', to='blingaleague.Member'),
        ),
        migrations.AlterField(
            model_name='tradedasset',
            name='sender',
            field=models.ForeignKey(related_name='assets_sent', to='blingaleague.Member'),
        ),
    ]
