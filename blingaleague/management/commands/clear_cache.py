import datetime

from django.conf import settings
from django.core.cache import caches
from django.core.management.base import LabelCommand


class Command(LabelCommand):

    label = 'caches_to_clear'

    def handle_label(self, *caches_to_clear, **kwargs):
        if 'ALL' in caches_to_clear:
            print('\'ALL\' passed as an argument; will clear all caches')
            caches_to_clear = settings.CACHES.keys()

        for cache_name in caches_to_clear:
            try:
                cache = caches[cache_name]
            except Exception:
                raise ValueError(
                    "Cache {} does not exist".format(cache_name),
                )
            cache.clear()
            print("{} cached cleared".format(cache_name))
