from django.core.management.base import BaseCommand

from blingalytics.utils import CACHE, PLAYOFF_ODDS_QUEUE_CACHE_KEY, \
                   PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY


class Command(BaseCommand):

    label = 'caches_to_clear'

    def handle(self, *args, **kwargs):
        CACHE.delete(PLAYOFF_ODDS_QUEUE_CACHE_KEY)
        CACHE.delete(PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY)
