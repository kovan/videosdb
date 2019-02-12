from django.core.management.base import BaseCommand, CommandError
from videosdb_code import Main, IPFS

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-t", "--trace", action="store_true")
        parser.add_argument("-c", "--check-for-new-videos", action="store_true")
        parser.add_argument("-n", "--publish-next", action="store_true")
        parser.add_argument("-a", "--publish-all", action="store_true")
        parser.add_argument("--republish-all", action="store_true")
        parser.add_argument("--only-update-dnslink", action="store_true")
        parser.add_argument("--as-draft", action="store_true")
        parser.add_argument("--regen-ipfs-folder", action="store_true")
        parser.add_argument("--update-dnslink", action="store_true")

    def handle(self, *args, **options):

        import yaml
        with open("config.yaml") as f:
            config = yaml.load(f)

        main = Main(config, options["trace"])

        if options["regen_ipfs_folder"]:
            main.regen_ipfs_folder()

        if options["check_for_new_videos"]:
            main.check_for_new_videos()

        if options["republish_all"]:
            main.republish_all()

        if options["publish_all"]:
            main.publish_all()

        if options["publish_next"]:
            main.publish_next(options["as_draft"])

        if options["update_dnslink"]:
            ipfs = IPFS(config)
            ipfs.update_dnslink(True)

        

