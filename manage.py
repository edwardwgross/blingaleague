#!/usr/bin/env python
from __future__ import absolute_import

if __name__ == '__main__':
    import os, sys, site

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
