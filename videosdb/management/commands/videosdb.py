from django.core.management.base import BaseCommand, CommandError
from videosdb_code import Main, IPFS

class Command(BaseCommand):

    def add_arguments(self, parser):
        #parser.add_argument("-v", "--verbose", action="store_true")
        parser.add_argument("-t", "--trace", action="store_true")
        parser.add_argument("-e", "--enqueue", action="store_true")
        parser.add_argument("-n", "--publish-next", action="store_true")
        parser.add_argument("--publish-all", action="store_true")
        parser.add_argument("--republish-all", action="store_true")
        parser.add_argument("--download-one", metavar="VIDEO-ID")
        parser.add_argument("--download-all", action="store_true")
        parser.add_argument("--only-update-dnslink", action="store_true")
        parser.add_argument("--as-draft", action="store_true")
        parser.add_argument("--regen-ipfs-folder", action="store_true")

    def handle(self, *args, **options):

        #if args.verbose:
        #    logging.getLogger("executor").setLevel(logging.DEBUG)
        #    logging.getLogger().setLevel(logging.DEBUG)

        #if args.trace:
            #logger.setLevel(TRACE)

        if options["only_update_dnslink"]:
            ipfs = IPFS()
            ipfs.update_dnslink(True)
            return

        main = Main()

        if options["regen_ipfs_folder"]:
            main.regen_ipfs_folder()

        if options["enqueue"]:
            main.enqueue()

        if options["republish_all"]:
            main.republish_all()

        if options["download_all"]:
            main.download_all()

        if options["publish_all"]:
            main.publish_all()

        if options["download_one"]:
            main.download_one(options["download_one"])

        if options["publish_next"]:
            main.publish_next(options["as_draft"])

        

