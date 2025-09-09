import logging

from django.core.management.base import BaseCommand

from blingaleague.models import pre_build_cache


class Command(BaseCommand):

    label = 'caches_to_clear'

    def handle(self, *args, **kwargs):
        pre_build_cache()
