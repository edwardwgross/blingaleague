# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0024_futuregame'),
    ]

    operations = [
        migrations.CreateModel(
            name='RingOfHonoree',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=200)),
                ('team', models.ForeignKey(related_name='rin_of_honorees', to='blingaleague.Member')),
            ],
            bases=(models.Model, blingaleague.models.ComparableObject),
        ),
    ]
