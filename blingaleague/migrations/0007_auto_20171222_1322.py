# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0006_member_defunct'),
    ]

    operations = [
        migrations.AlterField(
            model_name='season',
            name='place_1',
            field=models.ForeignKey(related_name=b'first_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
        migrations.AlterField(
            model_name='season',
            name='place_2',
            field=models.ForeignKey(related_name=b'second_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
        migrations.AlterField(
            model_name='season',
            name='place_3',
            field=models.ForeignKey(related_name=b'third_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
        migrations.AlterField(
            model_name='season',
            name='place_4',
            field=models.ForeignKey(related_name=b'fourth_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
        migrations.AlterField(
            model_name='season',
            name='place_5',
            field=models.ForeignKey(related_name=b'fifth_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
        migrations.AlterField(
            model_name='season',
            name='place_6',
            field=models.ForeignKey(related_name=b'sixth_place_finishes', default=None, blank=True, to='blingaleague.Member', null=True),
        ),
    ]
