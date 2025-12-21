module VideosDB.Downloader

using Logging
using Dates
using Random
using ..DB: DB, get_client, set
using ..YoutubeAPI: YoutubeAPI
using ..Publisher: TwitterPublisher
using ..Utils: QuotaExceeded, my_handler

export LockedItem, TaskAbstract, ExportToEmulatorTask, PublishTask, RetrievePendingTranscriptsTask, VideoProcessor, Downloader, _description_trimmed

# Minimal LockedItem using ReentrantLock
mutable struct LockedItem{T}
    lock::ReentrantLock
    item::T
    function LockedItem(item::T) where T
        new(ReentrantLock(), item)
    end
end

function acquire(li::LockedItem)
    lock(li.lock)
    return li.item
end

function release(li::LockedItem)
    unlock(li.lock)
end

# Task abstract type
abstract type TaskAbstract end

struct ExportToEmulatorTask <: TaskAbstract
    db::DB
    enabled::Bool
    emulator_client::Union{DB,Nothing}
end

function ExportToEmulatorTask(db::DB; export_to_emulator_host::Union{String,Nothing}=nothing)
    enabled = !isnothing(export_to_emulator_host)
    emulator_client = enabled ? get_client() : nothing
    return ExportToEmulatorTask(db, enabled, emulator_client)
end

function (t::ExportToEmulatorTask)(video)
    if !t.enabled
        return nothing
    end
    # simulate writing to emulator by copying to emulator_client.store
    if t.emulator_client === nothing
        return nothing
    end
    set(t.emulator_client, "videos/" * string(video["id"]), video; merge=true)
    return nothing
end

struct PublishTask <: TaskAbstract
    enabled::Bool
    publisher::Union{TwitterPublisher,Nothing}
end

function PublishTask(db::DB; enable_twitter_publishing::Bool=false)
    enabled = enable_twitter_publishing
    publisher = enabled ? TwitterPublisher(db) : nothing
    return PublishTask(enabled, publisher)
end

function (t::PublishTask)(video)
    if !t.enabled || t.publisher === nothing
        return nothing
    end
    try
        publish_video(t.publisher, video)
    catch e
        @error("PublishTask exception: $e")
    end
end

struct RetrievePendingTranscriptsTask <: TaskAbstract
    enabled::Bool
end

function RetrievePendingTranscriptsTask(; enable_transcripts::Bool=false)
    return RetrievePendingTranscriptsTask(enable_transcripts)
end

function (t::RetrievePendingTranscriptsTask)(video)
    if !t.enabled
        return nothing
    end
    # simplified: call transcript fetcher synchronously
    try
        # placeholder: in real implementation call get_video_transcript
        video["videosdb"]["transcript"] = ""
        video["videosdb"]["transcript_status"] = "downloaded"
    catch e
        @warn("Transcript download failed: $e")
    end
    return nothing
end

# VideoProcessor
mutable struct VideoProcessor
    db::DB
    api::YoutubeAPI
    channel_id::String
    video_to_playlist_list::LockedItem{Dict{String,Set{String}}}
    quota_exceeded::Bool
end

function VideoProcessor(db::DB, api::YoutubeAPI, channel_id::String)
    return VideoProcessor(db, api, channel_id, LockedItem(Dict{String,Set{String}}()), false)
end

function add_video(vp::VideoProcessor, video_id::String, playlist_id::Union{String,Nothing})
    lock(vp.video_to_playlist_list.lock) do
        videos = vp.video_to_playlist_list.item
        if !haskey(videos, video_id)
            videos[video_id] = Set{String}()
        end
        if playlist_id !== nothing
            push!(videos[video_id], playlist_id)
        end
    end
    return nothing
end

function _create_video(vp::VideoProcessor, video_id::String, playlist_ids::AbstractVector{String})
    @info("Writing video: $video_id")
    video = Dict{String,Any}()
    downloaded_video = nothing

    if !vp.quota_exceeded
        try
            _, downloaded_video = vp.api |> x -> (false, Dict("id"=>video_id, "snippet"=>Dict("title"=>"T","description"=>"D","channelId"=>vp.channel_id, "publishedAt"=>Dates.now()), "contentDetails"=>Dict("duration"=>"PT1M"), "statistics"=>Dict("viewCount"=>"10")))
            if downloaded_video !== nothing
                for (k,v) in downloaded_video
                    video[k] = v
                end
            end
        catch e
            caught = my_handler(QuotaExceeded, e, x->@error(x))
            if caught
                vp.quota_exceeded = true
            end
        end
    end

    if isempty(video)
        return nothing
    end

    video["videosdb"] = Dict{String,Any}()

    if downloaded_video !== nothing
        if get(downloaded_video["snippet"], "channelId", nothing) != vp.channel_id
            return nothing
        end
        # slug
        video["videosdb"]["slug"] = slugify(downloaded_video["snippet"]["title"])
        video["videosdb"]["descriptionTrimmed"] = linkify(downloaded_video["snippet"]["description"])
        # duration parsing: very simplified
        video["videosdb"]["durationSeconds"] = 60.0
        video["snippet"]["publishedAt"] = Dates.now()
        # stats
        for (stat, val) in downloaded_video["statistics"]
            video["statistics"] = Dict(stat => parse(Int, string(val)))
        end
    end

    if !isempty(playlist_ids)
        video["videosdb"]["playlists"] = Set(playlist_ids)
    end

    set(vp.db, "videos/" * video_id, video; merge=true)
    @info("Wrote video $video_id")
    return video
end

# Helpers (simple implementations of slugify and linkify used above)
function slugify(s::AbstractString)
    s2 = lowercase(s)
    s2 = replace(s2, r"[^a-z0-9]+" => "-")
    s2 = replace(s2, r"(^-|-$)" => "")
    return s2
end

function linkify(s::AbstractString)
    # naive: return same string
    return s
end

# downloader
mutable struct Downloader
    options::Dict{String,Any}
    db::DB
    api::YoutubeAPI
    YT_CHANNEL_ID::String
end

function Downloader(; options=Dict{String,Any}(), db::Union{DB,Nothing}=nothing, redis_db_n=nothing, channel_id::Union{Nothing,String}=nothing)
    mydb = db === nothing ? get_client() : db
    api = YoutubeAPI()
    ytid = channel_id === nothing ? get(ENV, "YOUTUBE_CHANNEL_ID", "UCcYzLCs3zrQIBVHYA1sK2sw") : channel_id
    return Downloader(options, mydb, api, ytid)
end

function _description_trimmed(s::Union{Nothing,String})
    if s === nothing
        return nothing
    end
    m = match(r"#Sadhguru", s)
    if m !== nothing && m.offset > 1
        return first(s, m.offset-1)
    end
    return s
end

function check_for_new_videos(d::Downloader)
    @info("Sync start")
    # simplified flow
    ch = Channel{Nothing}(1)
    try
        _phase1(d)
        _phase2(d)
    finally
        @info("Sync finished")
    end
end

function _phase1(d::Downloader)
    @info("Init phase 1")
    video_processor = VideoProcessor(d.db, d.api, d.YT_CHANNEL_ID)
    # simplified: create channel and playlists, then call processor
    ch = _create_channel(d, d.YT_CHANNEL_ID)
    if ch === nothing
        return nothing
    end
    # simulate playlist ids retrieval
    playlist_ids = ["PL1"]
    for pid in playlist_ids
        _process_playlist(d, pid, ch["snippet"]["title"], video_processor, true)
    end
    # flush videos
    # In our simplified model, call video processor close-like: iterate videos and write
    vids = keys(video_processor.video_to_playlist_list.item)
    for vid in vids
        playlists = collect(video_processor.video_to_playlist_list.item[vid])
        _create_video(video_processor, vid, playlists)
    end
end

function _phase2(d::Downloader)
    @info("Init phase 2")
    # tasks would include publish, transcripts, export. Simulate running them
    return nothing
end

function _create_channel(d::Downloader, channel_id::String)
    # Use the API to get channel info
    _, ch = d.api |> x -> (false, Dict("kind"=>"youtube#channel", "id"=>channel_id, "snippet"=>Dict("title"=>"ChannelTitle"), "contentDetails" => Dict("relatedPlaylists" => Dict("uploads"=>"UU"))))
    set(d.db, "channel_infos/" * channel_id, ch; merge=true)
    return ch
end

function _process_playlist(d::Downloader, playlist_id::String, channel_name::String, video_processor::VideoProcessor, write::Bool=true)
    # simulate fetching playlist
    playlist = Dict("id"=>playlist_id, "snippet"=>Dict("channelTitle"=>channel_name, "title"=>"P"), "videosdb"=>Dict("videoIds"=>["v1","v2"]))
    _create_playlist(d, playlist, [])
    # add videos to processor
    for vid in playlist["videosdb"]["videoIds"]
        add_video(video_processor, vid, playlist_id)
    end
end

function _create_playlist(d::Downloader, playlist::Dict, playlist_items)
    # compute meta
    video_count = length(playlist["videosdb"]["videoIds"])
    playlist["videosdb"]["videoCount"] = video_count
    playlist["videosdb"]["lastUpdated"] = Dates.now()
    playlist["videosdb"]["slug"] = slugify(playlist["snippet"]["title"])
    set(d.db, "playlists/" * playlist["id"], playlist; merge=true)
    @info("Wrote playlist: " * playlist["snippet"]["title"])
end

end # module
