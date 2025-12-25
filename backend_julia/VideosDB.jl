# ============================================================================
# VideosDB.jl - Complete YouTube Channel Database Synchronization System
# ============================================================================
module VideosDB

# Module exports
using .Utils
using .DB
using .YoutubeAPI
using .Publisher
using .Downloader

export Utils, DB, YoutubeAPI, Publisher, Downloader
export VideoDownloader, check_for_new_videos!, DownloadOptions
export DatabaseClient, YouTubeClient

end # module VideosDB