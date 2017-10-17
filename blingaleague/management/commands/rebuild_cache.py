from django.core.management.base import BaseCommand

from blingaleague.models import rebuild_whole_cache

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        rebuild_whole_cache()
