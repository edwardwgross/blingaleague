# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import blingacontent.utils


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0009_gazette_email_sent'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gazette',
            options={'ordering': ['publish_flag', '-published_date']},
        ),
        migrations.AlterModelOptions(
            name='meme',
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='gazette',
            name='body',
            field=models.TextField(blank=True, null=True, default=blingacontent.utils.new_gazette_body_template),
        ),
    ]
