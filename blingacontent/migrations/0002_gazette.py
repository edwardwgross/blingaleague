# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blingacontent', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gazette',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('headline', models.CharField(max_length=500)),
                ('published_date', models.DateField(default=None)),
                ('body', models.TextField(blank=True, null=True)),
                ('slug_url', models.CharField(max_length=200)),
            ],
        ),
    ]
