# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0021_auto_20220817_1637'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='draftpick',
            unique_together=set([('year', 'round', 'pick_in_round')]),
        ),
    ]
