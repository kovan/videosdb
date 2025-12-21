module VideosDB.Settings

using Logging
using Dates

# Constants translated from settings.py
const IPFS_HOST = get(ENV, "IPFS_HOST", "127.0.0.1")
const IPFS_PORT = parse(Int, get(ENV, "IPFS_PORT", "5001"))

const VIDEOSDB_DOMAIN = "sadhguru.digital"
const VIDEOSDB_DNSZONE = "sadhguru"
const YOUTUBE_CHANNEL = Dict("id" => "UCcYzLCs3zrQIBVHYA1sK2sw", "name" => "Sadhguru")
const TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
const VIDEO_FILES_DIR = get(ENV, "VIDEO_FILES_DIR", "/mnt/videos")

const YOUTUBE_KEY = get(ENV, "YOUTUBE_KEY", "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU")
const YOUTUBE_KEY_TESTING = get(ENV, "YOUTUBE_KEY_TESTING", "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs")

"""
Setup the global logger. Level can be a `Logging.LogLevel` or a string like "INFO".
"""
function setup_logging(level::Union{Logging.LogLevel,String}=Logging.Info)
    lvl = level isa String ? Logging.parselevel(level) : level
    logger = Logging.ConsoleLogger(stdout, min_level = lvl)
    global_logger(logger)
end

end # module
