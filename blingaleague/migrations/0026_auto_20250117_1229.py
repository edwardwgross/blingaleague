# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0025_ringofhonoree'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='playernotes',
            options={'verbose_name_plural': 'player notes'},
        ),
        migrations.AlterModelOptions(
            name='ringofhonoree',
            options={'ordering': ('team', 'name')},
        ),
        migrations.AlterField(
            model_name='ringofhonoree',
            name='team',
            field=models.ForeignKey(related_name='ring_of_honorees', to='blingaleague.Member'),
        ),
        migrations.AlterUniqueTogether(
            name='ringofhonoree',
            unique_together=set([('name', 'team')]),
        ),
    ]
