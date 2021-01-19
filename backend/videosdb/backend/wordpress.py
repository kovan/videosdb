import logging
import os
import re
from autologging import traced, TRACE
from django.conf import settings




@traced(logging.getLogger("videosdb"))
class Wordpress:
    def __init__(self):
        from wordpress_xmlrpc import Client
        self.client = Client(
            settings.WWW_ROOT +   "/xmlrpc.php",
            settings.WP_USERNAME,
            settings.WP_PASS)

    def upload_image(self, file, title):
        from wordpress_xmlrpc.compat import xmlrpc_client
        from wordpress_xmlrpc.methods import media

        images = self.client.call(media.GetMediaLibrary({
            number:1,
            "parent_id":0
        }))
        found = [img for img in images if img.title == title + ".jpg"]
        if found: # do not reupload
            return int(found[0].id)

        data = {
            "name": title + ".jpg",
            'type': 'image/jpeg',
            "bits": xmlrpc_client.Binary(file.read())
        }

        return self.client.call(media.UploadFile(data))["id"]

    def find_image(self, image_id):
        from wordpress_xmlrpc.methods import media
        return self.client.call(media.GetMediaItem(image_id))

    def delete(self, post_id):
        from wordpress_xmlrpc.methods.posts import DeletePost
        return self.client.call(DeletePost(post_id))

    def get(self, post_id):
        from wordpress_xmlrpc.methods.posts import GetPost
        return self.client.call(GetPost(post_id))

    def get_all(self, filter):
        from wordpress_xmlrpc.methods.posts import GetPosts
        return self.client.call(GetPosts(filter))

    def publish(self, video, post_id = 0, thumbnail_id = 0):
        from wordpress_xmlrpc import WordPressPost
        from wordpress_xmlrpc.methods.posts import NewPost, EditPost
        import jinja2
        template_raw = open(os.path.dirname(__file__) + "/post.jinja2").read()
        description = ""
        if video.description:
            # leave part of description specific to this video:
            match = re.search(settings.TRUNCATE_DESCRIPTION_AFTER, video.description)
            if match and match.start() != -1:
                description = video.description[:match.start()]
            else:
                description = video.description

        transcript = ""
        if video.transcript:
            transcript = video.transcript


        template = jinja2.Template(template_raw)
        html = template.render(
            youtube_id=video.youtube_id,
            description=description,
            transcript=transcript
        )

        post = WordPressPost()
        post.excerpt = description
        post.title = video.title
        post.content = html
        if thumbnail_id:
            post.thumbnail = thumbnail_id
        post.custom_fields = [{
            "key": "youtube_id",
            "value": video.youtube_id
        }]

        post.terms_names = {}

        if video.categories:
            post.terms_names["category"] = [str(c) for c in video.categories.all()]
        
        if video.tags:
            post.terms_names["post_tag"] = [str(t) for t in video.tags.all()]

        post.post_status = "publish"

        logging.debug("publishing " + str(post_id))
        
        if post_id:
            self.client.call(EditPost(post_id, post))
            return post_id

        return int(self.client.call(NewPost(post)))

