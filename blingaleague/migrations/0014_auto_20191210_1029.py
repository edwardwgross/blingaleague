# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0013_auto_20191210_0742'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tradedasset',
            options={'ordering': ['trade', 'receiver', 'keeper_cost', 'name']},
        ),
        migrations.AddField(
            model_name='tradedasset',
            name='sender',
            field=models.ForeignKey(default=1, related_name='traded_away', to='blingaleague.Member'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='tradedasset',
            name='receiver',
            field=models.ForeignKey(related_name='traded_for', to='blingaleague.Member'),
        ),
    ]
