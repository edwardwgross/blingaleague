import datetime

from django.core.cache import caches
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        default_cache = caches['default']
        default_cache.clear()
        print("{}: cached cleared".format(datetime.datetime.now()))
