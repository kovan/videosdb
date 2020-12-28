from videosdb.backend import code
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    def add_arguments(self, parser):
        code.add_arguments(parser)

    def handle(self, *args, **options):
        code.handle(*args, **options)


        

