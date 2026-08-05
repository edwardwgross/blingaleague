# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingaleague.models


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0026_auto_20250117_1229'),
    ]

    operations = [
        migrations.CreateModel(
            name='DraftOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('year', models.IntegerField(db_index=True)),
                ('pick', models.IntegerField(db_index=True)),
                ('team', models.ForeignKey(related_name='draft_order', to='blingaleague.Member')),
            ],
            options={
                'ordering': ['year', 'pick'],
            },
            bases=(models.Model, blingaleague.models.ComparableObject),
        ),
        migrations.AlterUniqueTogether(
            name='draftorder',
            unique_together=set([('year', 'pick')]),
        ),
    ]
