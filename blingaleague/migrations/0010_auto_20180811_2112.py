# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0009_auto_20180624_1200'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Meme',
        ),
        migrations.AddField(
            model_name='fakemember',
            name='associated_member',
            field=models.ForeignKey(blank=True, null=True, default=None, related_name='co_managers', to='blingaleague.Member'),
        ),
    ]
