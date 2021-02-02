from videosdb.models import Video


def run():
    for video in Video.objects.using("sqlite").filter(excluded=False):
        try:
            v = Video.objects.get(youtube_id=video.youtube_id)
            if v.transcript_available and v.transcript:
                video.transcript = v.transcript
                video.save()
        except:
            pass
