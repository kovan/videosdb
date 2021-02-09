import os
import logging
import sys
from autologging import traced
import ipfshttpclient
from django.conf import settings


@traced(logging.getLogger(__name__))
class DNS:
    def __init__(self, dns_zone):
        self.dns_zone = dns_zone
        path = os.path.dirname(sys.modules[__name__].__file__)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path + "/creds.json"

    def _update_record(self, record_name, record_type, ttl, new_value):
        from google.cloud import dns
        if not self.dns_zone:
            return

        client = dns.Client()
        zone = client.zone(self.dns_zone)
        records = zone.list_resource_record_sets()

        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == record_name + "." and record.record_type == record_type:
                changes.delete_record_set(record)
        # add new
        record = zone.resource_record_set(
            record_name + ".", record_type, ttl, [new_value, ])
        changes.add_record_set(record)
        # finish transaction
        changes.create()

    def update_dnslink(self, record_name, new_root_hash):
        self._update_record(record_name, "TXT", 300,
                            "dnslink=/ipfs/" + new_root_hash)

    def update_ip(self, record_name, new_ip):
        self._update_record(record_name, "A", 300, new_ip)


@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self):

        self.host = settings.IPFS_HOST
        self.port = settings.IPFS_PORT
        self.dnslink_update_pending = False
        self.api = ipfshttpclient.connect(
            "/ip4/%s/tcp/%s/http" % (self.host, self.port))
#        self.api = ipfsapi.connect(self.host, self.port)

    def add_file(self, filename, opts={}, add_to_dir=True):
        ipfs_hash = self.api.add(filename, opts)["Hash"]
        self.api.pin.add(ipfs_hash)

        if add_to_dir:
            self.add_to_dir(filename, ipfs_hash)

        return ipfs_hash

    def add_to_dir(self, filename, _hash):
        from ipfshttpclient.exceptions import StatusError
        src = "/ipfs/" + _hash
        dst = "/videos/" + filename
        try:
            self.api.files.rm(dst)
        except StatusError:
            pass
        self.api.files.mkdir("/videos", parents=True)
        self.api.files.cp(src, dst)
        self.dnslink_update_pending = True

    def get_file(self, ipfs_hash):
        self.api.get(ipfs_hash)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def update_dnslink(self, force=False):
        if not self.dnslink_update_pending and not force:
            return

        root_hash = self.api.files.stat("/videos")["Hash"]
        dns = DNS(self.config["dns_zone"])
        dns.update_dnslink(self.config["dnslink"], root_hash)
        self.dnslink_update_pending = False
