import logging
from autologging import traced, TRACE
from videosdb.models import Video, Publication
from .wordpress import Wordpress
#import videosdb.backend.code


@traced(logging.getLogger(__name__))
class Publisher:
    def __init__(self):
        self.wordpress = Wordpress()

    def publish_one(self, video):
        from django.utils import timezone
        if type(video) is not Video:
            video = Video.objects.get(youtube_id=video)

        if Publication.objects.filter(video=video).count():
            pub = Publication.objects.get(video=video)
            self.wordpress.publish(video, pub.post_id, pub.thumbnail_id)
        else:
            pub = Publication(video=video)
            if video.thumbnail:
                f = video.thumbnail.open()
                pub.thumbnail_id = self.wordpress.upload_image(
                    f.open(), video.youtube_id)
                f.close()

            pub.post_id = self.wordpress.publish(video, 0, pub.thumbnail_id)

        pub.published_date = timezone.now()
        pub.save()

        return pub

    def unpublish_one(self, publication):
        self.wordpress.delete(publication.post_id)
        publication.delete()

    def sync_wordpress(self):
        videos = Video.objects.filter(
            excluded=False).order_by("yt_published_date")
        for video in videos:
            if not hasattr(video, "publication") \
                    or not video.publication.published_date \
                    or video.publication.published_date < video.modified_date:
                self.publish_one(video)

        for pub in Publication.objects.all():
            if pub.video not in videos:
                self.unpublish_one(pub)

    def republish_all(self):
        for pub in Publication.objects.all():
            self.publish_one(pub.video)
