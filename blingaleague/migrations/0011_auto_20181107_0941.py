# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0010_auto_20180811_2112'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fakemember',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='member',
            options={'ordering': ['first_name', 'last_name']},
        ),
        migrations.AlterModelOptions(
            name='season',
            options={'ordering': ['-year']},
        ),
        migrations.AddField(
            model_name='member',
            name='use_nickname',
            field=models.BooleanField(default=False),
        ),
    ]
