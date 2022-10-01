# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0022_auto_20220817_1639'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerNotes',
            fields=[
                ('name', models.CharField(primary_key=True, max_length=200, serialize=False)),
                ('nickname', models.CharField(max_length=200, blank=True, null=True)),
                ('rip_in_peace', models.BooleanField(default=False)),
            ],
            bases=(models.Model, blingaleague.models.ComparableObject),
        ),
        migrations.AlterUniqueTogether(
            name='draftpick',
            unique_together=set([]),
        ),
    ]
