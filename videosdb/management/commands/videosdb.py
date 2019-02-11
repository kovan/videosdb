from django.core.management.base import BaseCommand, CommandError
from videosdb_code import Main, IPFS

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-t", "--trace", action="store_true")
        parser.add_argument("-e", "--enqueue", action="store_true")
        parser.add_argument("-n", "--publish-next", action="store_true")
        parser.add_argument("--publish-all", action="store_true")
        parser.add_argument("--republish-all", action="store_true")
        parser.add_argument("--only-update-dnslink", action="store_true")
        parser.add_argument("--as-draft", action="store_true")
        parser.add_argument("--regen-ipfs-folder", action="store_true")

    def handle(self, *args, **options):

        main = Main(options["trace"])

        if options["regen_ipfs_folder"]:
            main.regen_ipfs_folder()

        if options["enqueue"]:
            main.enqueue()

        if options["republish_all"]:
            main.republish_all()

        if options["publish_all"]:
            main.publish_all()

        if options["publish_next"]:
            main.publish_next(options["as_draft"])

        

