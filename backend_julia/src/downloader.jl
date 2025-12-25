
# ============================================================================
# Downloader Module
# ============================================================================
module Downloader

using Logging
using Dates
using Random
using ..DB
using ..YoutubeAPI
using ..Utils
using ..Publisher
import ..DB: DatabaseClient, READS, WRITES
import ..YoutubeAPI: YouTubeClient
import ..Utils: QuotaExceeded, my_handler

export VideoDownloader, check_for_new_videos!, DownloadOptions

struct DownloadOptions
    enable_transcripts::Bool
    enable_twitter_publishing::Bool
    export_to_emulator_host::Union{String, Nothing}
    
    DownloadOptions(; 
        enable_transcripts=false,
        enable_twitter_publishing=false,
        export_to_emulator_host=nothing
    ) = new(enable_transcripts, enable_twitter_publishing, export_to_emulator_host)
end

abstract type Task end

mutable struct LockedItem{T}
    lock::ReentrantLock
    item::T
    
    LockedItem(item::T) where T = new{T}(ReentrantLock(), item)
end

mutable struct ExportToEmulatorTask <: Task
    db::DatabaseClient
    options::Union{DownloadOptions, Nothing}
    enabled::Bool
    emulator_client::Union{DatabaseClient, Nothing}
    
    function ExportToEmulatorTask(db, options=nothing, nursery=nothing)
        enabled = !isnothing(options) && !isnothing(options.export_to_emulator_host)
        
        emulator_client = nothing
        if enabled
            previous_emu = get(ENV, "FIRESTORE_EMULATOR_HOST", nothing)
            ENV["FIRESTORE_EMULATOR_HOST"] = options.export_to_emulator_host
            emulator_client = DB.get_client()
            
            if !isnothing(previous_emu)
                @debug "Restoring emulator host"
                ENV["FIRESTORE_EMULATOR_HOST"] = previous_emu
            else
                delete!(ENV, "FIRESTORE_EMULATOR_HOST")
            end
        end
        
        new(db, options, enabled, emulator_client)
    end
end

function (task::ExportToEmulatorTask)(video::Dict)
    !task.enabled && return
    @debug "Exporting video $(video["id"]) to emulator"
end

function export_pending_collections(task::ExportToEmulatorTask)
    !task.enabled && return
    @info "Exporting pending collections to emulator"
end

mutable struct PublishTask <: Task
    db::DatabaseClient
    options::Union{DownloadOptions, Nothing}
    enabled::Bool
    publisher::Union{Publisher.TwitterPublisher, Nothing}
    
    function PublishTask(db, options=nothing, nursery=nothing)
        enabled = !isnothing(options) && options.enable_twitter_publishing
        publisher = enabled ? Publisher.TwitterPublisher(db) : nothing
        new(db, options, enabled, publisher)
    end
end

function (task::PublishTask)(video::Dict)
    !task.enabled && return
    
    try
        Publisher.publish_video(task.publisher, video)
    catch e
        @error "Twitter publishing error" exception=e
    end
end

mutable struct RetrievePendingTranscriptsTask <: Task
    db::DatabaseClient
    options::Union{DownloadOptions, Nothing}
    nursery::Union{Channel, Nothing}
    enabled::Bool
    capacity_limiter::Semaphore
    
    function RetrievePendingTranscriptsTask(db, options=nothing, nursery=nothing)
        enabled = !isnothing(options) && options.enable_transcripts
        capacity_limiter = Semaphore(10)
        new(db, options, nursery, enabled, capacity_limiter)
    end
end

function (task::RetrievePendingTranscriptsTask)(video::Dict)
    !task.enabled && return
    
    if !isnothing(task.nursery)
        @async handle_transcript(task, video)
    end
end

function handle_transcript(task::RetrievePendingTranscriptsTask, video::Dict)
    current_status = get(get(video, "videosdb", Dict()), "transcript_status", nothing)
    
    if current_status ∉ ("pending", nothing)
        return
    end
    
    @info "Downloading transcript for video: $(video["id"]) because its status is $current_status"
    
    transcript, new_status = download_transcript(video["id"], task.capacity_limiter)
    
    if new_status == current_status
        return
    end
    
    video_updated = merge(video, Dict(
        "videosdb" => merge(
            get(video, "videosdb", Dict()),
            Dict(
                "transcript_status" => new_status,
                "transcript" => transcript
            )
        )
    ))
    
    DB.set_doc!(task.db, "videos/$(video["id"])", video_updated; merge=true)
end

function download_transcript(video_id::String, capacity_limiter::Semaphore)
    try
        Base.acquire(capacity_limiter)
        transcript = YoutubeAPI.get_video_transcript(video_id)
        Base.release(capacity_limiter)
        return transcript, "downloaded"
    catch e
        Base.release(capacity_limiter)
        @warning "Could not retrieve transcript: $e"
        return nothing, "unavailable"
    end
end

mutable struct VideoProcessor
    _db::DatabaseClient
    _api::YouTubeClient
    _channel_id::String
    _video_to_playlist_list::LockedItem{Dict{String, Set{String}}}
    _quota_exceeded::Bool
    
    function VideoProcessor(db, api, channel_id)
        videos_dict = Dict{String, Set{String}}()
        locked_item = LockedItem(videos_dict)
        new(db, api, channel_id, locked_item, false)
    end
end

function Base.close(vp::VideoProcessor)
    lock(vp._video_to_playlist_list.lock) do
        videos = vp._video_to_playlist_list.item
        video_ids = collect(keys(videos))
        @info "Writing $(length(video_ids)) videos"
        shuffle!(video_ids)
        
        @sync for video_id in video_ids
            playlists = videos[video_id]
            @async create_video(vp, video_id, playlists)
        end
    end
end

function add_video(vp::VideoProcessor, video_id::String, playlist_id::Union{String, Nothing})
    @debug "Processing playlist item video $video_id, playlist $playlist_id"
    
    lock(vp._video_to_playlist_list.lock) do
        videos = vp._video_to_playlist_list.item
        if !haskey(videos, video_id)
            videos[video_id] = Set{String}()
        end
        if !isnothing(playlist_id)
            push!(videos[video_id], playlist_id)
        end
    end
end

function slugify(text::String)
    result = lowercase(text)
    result = replace(result, r"[^a-z0-9\s-]" => "")
    result = replace(result, r"\s+" => "-")
    result = strip(result, '-')
    return result
end

function linkify(text::String)
    return text
end

function parse_duration(duration_str::String)
    m = match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    isnothing(m) && return 0
    
    hours = isnothing(m.captures[1]) ? 0 : parse(Int, m.captures[1])
    minutes = isnothing(m.captures[2]) ? 0 : parse(Int, m.captures[2])
    seconds = isnothing(m.captures[3]) ? 0 : parse(Int, m.captures[3])
    
    return hours * 3600 + minutes * 60 + seconds
end

function parse_datetime_iso(dt_str::String)
    return now()
end

function create_video(vp::VideoProcessor, video_id::String, playlist_ids::Set{String})
    @info "Writing video: $video_id..."
    
    video = Dict{String, Any}()
    downloaded_video = nothing
    
    if !vp._quota_exceeded
        try
            _, downloaded_video = YoutubeAPI.get_video_info(vp._api, video_id)
            if !isnothing(downloaded_video)
                video = merge(video, Dict(pairs(downloaded_video)))
            end
        catch e
            exception_caught = my_handler(YoutubeAPI.YTQuotaExceeded, e, x -> @error("$x"))
            if exception_caught
                vp._quota_exceeded = true
            end
        end
    end
    
    isempty(video) && return
    
    video["videosdb"] = Dict{String, Any}()
    
    if !isnothing(downloaded_video)
        snippet = get(video, "snippet", Dict())
        channel_id = get(snippet, "channelId", "")
        
        if channel_id != vp._channel_id
            return
        end
        
        title = get(snippet, "title", "")
        description = get(snippet, "description", "")
        
        content_details = get(video, "contentDetails", Dict())
        duration = get(content_details, "duration", "PT0S")
        
        video["videosdb"] = merge(video["videosdb"], Dict(
            "slug" => slugify(title),
            "descriptionTrimmed" => linkify(description),
            "durationSeconds" => parse_duration(duration)
        ))
        
        published_at = get(snippet, "publishedAt", "")
        video["snippet"]["publishedAt"] = parse_datetime_iso(published_at)
        
        statistics = get(video, "statistics", Dict())
        for (stat, value) in statistics
            video["statistics"][stat] = parse(Int, string(value))
        end
    end
    
    if !isempty(playlist_ids)
        video["videosdb"]["playlists"] = collect(playlist_ids)
    end
    
    DB.set_doc!(vp._db, "videos/$video_id", video; merge=true)
    @info "Wrote video $video_id"
    
    return video
end

mutable struct VideoDownloader
    options::Union{DownloadOptions, Nothing}
    YT_CHANNEL_ID::String
    db::DatabaseClient
    api::YouTubeClient
    
    function VideoDownloader(; options=nothing, db=nothing, redis_db_n=nothing, channel_id=nothing)
        yt_channel_id = isnothing(channel_id) ? ENV["YOUTUBE_CHANNEL_ID"] : channel_id
        db_instance = isnothing(db) ? DatabaseClient() : db
        api_instance = YouTubeClient(db_instance; redis_db_n=redis_db_n)
        
        @debug "ENVIRONMENT:"
        @debug ENV
        
        new(options, yt_channel_id, db_instance, api_instance)
    end
end

function init(downloader::VideoDownloader)
    DB.init_db!(downloader.db)
end

function check_for_new_videos!(downloader::VideoDownloader)
    @info "Sync start"
    
    init(downloader)
    
    debug_task = @async print_debug_info(downloader, false)
    
    try
        phase1(downloader)
        phase2(downloader)
    finally
        print_debug_info(downloader, true)
    end
    
    @info "Sync finished"
end

function phase1(downloader::VideoDownloader)
    @info "Init phase 1"
    
    video_processor = VideoProcessor(downloader.db, downloader.api, downloader.YT_CHANNEL_ID)
    
    try
        channel = create_channel(downloader, downloader.YT_CHANNEL_ID)
        isnothing(channel) && return
        
        channel_name = channel.snippet.title
        playlist_ids = retrieve_all_playlist_ids(downloader, downloader.YT_CHANNEL_ID)
        
        @sync begin
            process_playlist_ids(downloader, playlist_ids, channel_name, video_processor)
            
            all_videos_playlist_id = channel.contentDetails.relatedPlaylists.uploads
            
            if !haskey(ENV, "DEBUG")
                process_playlist(downloader, all_videos_playlist_id, channel_name, 
                               video_processor, false)
            end
        end
        
        Base.close(video_processor)
    catch e
        my_handler(QuotaExceeded, e, x -> @error("$x"))
    end
end

function phase2(downloader::VideoDownloader)
    @info "Init phase 2"
    
    nursery = nothing
    args = (downloader.db, downloader.options, nursery)
    
    export_to_emulator_task = ExportToEmulatorTask(args...)
    tasks = [
        RetrievePendingTranscriptsTask(args...),
        PublishTask(args...),
        export_to_emulator_task,
        video_dict -> DB.validate_video_schema(downloader.db, video_dict)
    ]
    
    final_video_iteration(downloader, tasks)
    export_pending_collections(export_to_emulator_task)
end

function final_video_iteration(downloader::VideoDownloader, phase2_tasks::Vector)
    final_video_ids = LockedItem(Set{String}())
    
    @info "Processing videos for phase 2 tasks"
    
    video_ids = Set{String}()
    
    lock(final_video_ids.lock) do
        for video_id in video_ids
            push!(final_video_ids.item, video_id)
        end
    end
    
    for video_id in video_ids
        video_dict = Dict("id" => video_id)
        @debug "Applying tasks for video $video_id"
        
        for task in phase2_tasks
            task(video_dict)
        end
    end
    
    ids = final_video_ids.item
    if !isempty(ids)
        DB.set_noquota!(downloader.db, "meta/video_ids", 
                       Dict("videoIds" => collect(ids)))
    end
    
    final_videos_length = length(ids)
    if final_videos_length == 0
        throw(ErrorException("No videos to publish"))
    end
    
    @info "Final video list length: $final_videos_length"
    return ids
end

function process_playlist_ids(downloader::VideoDownloader, playlist_ids::Vector{String},
                              channel_name::String, video_processor::VideoProcessor)
    shuffle!(playlist_ids)
    
    @sync for playlist_id in playlist_ids
        @async process_playlist(downloader, playlist_id, channel_name, video_processor, true)
    end
end

function process_playlist(downloader::VideoDownloader, playlist_id::String,
                         channel_name::String, video_processor::VideoProcessor,
                         write::Bool=true)
    @info "Processing playlist $playlist_id"
    
    _, playlist = YoutubeAPI.get_playlist_info(downloader.api, playlist_id)
    isnothing(playlist) && return
    
    if playlist.snippet.channelTitle != channel_name
        return
    end
    
    _, playlist_items = YoutubeAPI.list_playlist_items(downloader.api, playlist_id)
    
    create_playlist(downloader, playlist, playlist_items, write)
    
    video_ids_set = get(get(playlist, "videosdb", Dict()), "videoIds", Set{String}())
    video_ids = collect(video_ids_set)
    shuffle!(video_ids)
    
    @sync for video_id in video_ids
        @async add_video(video_processor, video_id, write ? playlist_id : nothing)
    end
end

function retrieve_all_playlist_ids(downloader::VideoDownloader, channel_id::String)
    _, ids1 = YoutubeAPI.list_channelsection_playlist_ids(downloader.api, channel_id)
    _, ids2 = YoutubeAPI.list_channel_playlist_ids(downloader.api, channel_id)
    
    playlist_ids = Set{String}()
    
    for id in ids1
        push!(playlist_ids, id)
    end
    
    if !haskey(ENV, "DEBUG")
        for id in ids2
            push!(playlist_ids, id)
        end
    end
    
    @info "Retrieved all playlist IDs."
    return collect(playlist_ids)
end

function create_channel(downloader::VideoDownloader, channel_id::String)
    _, channel_info = YoutubeAPI.get_channel_info(downloader.api, channel_id)
    isnothing(channel_info) && return nothing
    
    @info "Processing channel: $(channel_info.snippet.title)"
    
    DB.set_doc!(downloader.db, "channel_infos/$channel_id", 
               Dict(pairs(channel_info)); merge=true)
    
    return channel_info
end

function create_playlist(downloader::VideoDownloader, playlist::Dict,
                        playlist_items::Channel, write::Bool=true)
    video_count = 0
    last_updated = nothing
    video_ids = Set{String}()
    
    for item in playlist_items
        snippet = get(item, "snippet", Dict())
        if get(snippet, "channelId", "") != downloader.YT_CHANNEL_ID
            continue
        end
        
        resource_id = get(snippet, "resourceId", Dict())
        video_id = get(resource_id, "videoId", "")
        
        if !isempty(video_id)
            push!(video_ids, video_id)
            video_count += 1
            
            published_at = get(snippet, "publishedAt", "")
            video_date = parse_datetime_iso(published_at)
            
            if isnothing(last_updated) || video_date > last_updated
                last_updated = video_date
            end
        end
    end
    
    playlist_snippet = get(playlist, "snippet", Dict())
    playlist_title = get(playlist_snippet, "title", "")
    
    playlist_updated = merge(playlist, Dict(
        "videosdb" => Dict(
            "videoCount" => video_count,
            "lastUpdated" => last_updated,
            "videoIds" => video_ids,
            "slug" => slugify(playlist_title)
        )
    ))
    
    if write
        playlist_id = get(playlist, "id", "")
        DB.set_doc!(downloader.db, "playlists/$playlist_id", 
                   playlist_updated; merge=true)
        @info "Wrote playlist: $playlist_title"
    end
end

function description_trimmed(description::Union{String, Nothing})
    isnothing(description) && return nothing
    m = match(r"#Sadhguru", description)
    if !isnothing(m)
        return description[1:m.offset-1]
    end
    return description
end

function print_debug_info(downloader::VideoDownloader, once::Bool=false)
    while true
        @info "Running tasks: $(Threads.nthreads())"
        @info "DB stats:"
        @info DB.get_stats(downloader.db)
        
        cache_stats = YoutubeAPI.stats(downloader.api.cache)
        @info "Cache stats:"
        @info cache_stats
        
        once && break
        sleep(120)
    end
end

end # module Downloader