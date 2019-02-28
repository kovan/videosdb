import videosdb_code
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    def add_arguments(self, parser):
        videosdb_code.add_arguments(parser)

    def handle(self, *args, **options):
        videosdb_code.handle(*args, **options)


        

