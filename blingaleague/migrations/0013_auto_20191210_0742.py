# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0012_auto_20191210_0522'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='trade',
            options={'ordering': ['-year', '-week', '-date']},
        ),
        migrations.AlterModelOptions(
            name='tradedasset',
            options={'ordering': ['-trade', 'receiver', 'keeper_cost', 'name']},
        ),
        migrations.RenameField(
            model_name='tradedasset',
            old_name='sender',
            new_name='receiver',
        ),
        migrations.AlterField(
            model_name='tradedasset',
            name='trade',
            field=models.ForeignKey(related_name='traded_assets', to='blingaleague.Trade'),
        ),
    ]
