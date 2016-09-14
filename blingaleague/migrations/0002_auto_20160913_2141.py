# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


INITIAL_MEMBERS = (
    {'first_name': 'Ed', 'last_name': 'Gross'},
    {'first_name': 'Matt', 'last_name': 'Harrison'},
    {'first_name': 'Rob', 'last_name': 'Gross'},
    {'first_name': 'Kevin', 'last_name': 'Pattermann'},
    {'first_name': 'Dave', 'last_name': 'Fultz'},
    {'first_name': 'Mike', 'last_name': 'Romor'},
    {'first_name': 'Adam', 'last_name': 'Pulley'},
    {'first_name': 'Mark', 'last_name': 'Babel'},
    {'first_name': 'Derrek', 'last_name': 'Drenckpohl'},
    {'first_name': 'Allen', 'last_name': 'Clark'},
    {'first_name': 'Katie', 'last_name': 'Gawne'},
    {'first_name': 'Nick', 'last_name': 'Warren', 'nickname': 'Rabbit'},
    {'first_name': 'Pat', 'last_name': 'Gawne'},
    {'first_name': 'Richie', 'last_name': 'Armour'},
    {'first_name': 'Mike', 'last_name': 'Schertz'},
)


def populate_initial_members(apps, schema_editor):
    Member = apps.get_model('blingaleague', 'Member')
    for initial_member in INITIAL_MEMBERS:
        member_obj = Member(**initial_member)
        member_obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('blingaleague', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_initial_members)
    ]
