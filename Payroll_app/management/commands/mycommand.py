from django.core.management.base import BaseCommand
from django.core.cache import caches

class Command(BaseCommand):
    def handle(self, *args, **options):
        cache = caches['default']
        # Cache operation...
