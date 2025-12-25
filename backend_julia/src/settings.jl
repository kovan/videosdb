const YOUTUBE_CHANNEL_ID = get(ENV, "YOUTUBE_CHANNEL_ID", "UCcYzLCs3zrQIBVHYA1sK2sw")
const YOUTUBE_KEY = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"
const YOUTUBE_KEY_TESTING = "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs"
const VIDEOSDB_DOMAIN = "sadhguru.digital"
const VIDEOSDB_DNSZONE = "sadhguru"
const TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
const VIDEO_FILES_DIR = "/mnt/videos"

const IPFS_HOST = get(ENV, "IPFS_HOST", "127.0.0.1")
const IPFS_PORT = get(ENV, "IPFS_PORT", "5001")

# Logging configuration
function setup_logging()
    logger = ConsoleLogger(stdout, get(ENV, "LOGLEVEL", Logging.Info))
    global_logger(logger)
end