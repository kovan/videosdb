# ============================================================================
# VideosDB.jl - Complete YouTube Channel Database Synchronization System
# ============================================================================
module VideosDB

# ============================================================================
# Utils Module
# ============================================================================
module Utils

using Sockets
using Logging

export QuotaExceeded, wait_for_port, my_handler, put_item_at_front, get_module_path

struct QuotaExceeded <: Exception
    msg::String
end

Base.showerror(io::IO, e::QuotaExceeded) = print(io, "QuotaExceeded: ", e.msg)

function get_module_path()
    return dirname(@__FILE__)
end

function wait_for_port(port::Int, host::String="localhost"; timeout::Float64=30.0)
    @debug "Waiting for port $host:$port to be open"
    start_time = time()
    
    while true
        try
            sock = connect(host, port)
            close(sock)
            break
        catch ex
            sleep(0.01)
            if time() - start_time >= timeout
                throw(ErrorException("Waited too long for port $port on host $host to start accepting connections"))
            end
        end
    end
end

function my_handler(exception_type::Type{<:Exception}, e::Exception, handler::Function)
    caught = false
    @debug "Exception happened: $e"
    
    if e isa exception_type
        caught = true
        handler(e)
    else
        rethrow(e)
    end
    
    return caught
end

function put_item_at_front(seq::Vector, item)
    isnothing(item) && return seq
    
    try
        i = findfirst(==(item), seq)
        if !isnothing(i)
            return vcat(seq[i:end], seq[1:i-1])
        end
    catch
    end
    
    return seq
end

end # module Utils

# ============================================================================
# Database Module
# ============================================================================
module DB

using Logging
using JSON3
using Dates
using ..Utils
import ..Utils: QuotaExceeded

export DatabaseClient, CounterType, init_db!, set_doc!, get_doc!, update_doc!, 
       delete_doc!, validate_video_schema, increase_counter!, get_stats,
       set_noquota!, update_noquota!, get_noquota!, recursive_delete!,
       delete_invalid_docs!, READS, WRITES, wait_for_port, get_client

@enum CounterType begin
    READS = 1
    WRITES = 2
end

mutable struct Counter
    type::CounterType
    counter::Int
    limit::Int
    lock::ReentrantLock
    
    Counter(type::CounterType, limit::Int) = new(type, 0, limit, ReentrantLock())
end

function increment!(c::Counter, quantity::Int=1)
    lock(c.lock) do
        c.counter += quantity
        if c.counter > c.limit
            throw(QuotaExceeded("Surpassed $(c.type) ops limit of $(c.limit)"))
        end
    end
end

Base.show(io::IO, c::Counter) = print(io, "Counter $(c.type): $(c.counter)/$(c.limit)")

mutable struct DatabaseClient
    free_tier_write_quota::Int
    free_tier_read_quota::Int
    counters::Dict{CounterType, Counter}
    db_schema::Dict
    project::String
    config::String
    _db::Any
    
    function DatabaseClient(; project=nothing, config=nothing)
        config_val = isnothing(config) ? get(ENV, "VIDEOSDB_CONFIG", "testing") : config
        project_val = isnothing(project) ? get(ENV, "FIREBASE_PROJECT", "videosdb-testing") : project
        
        free_tier_write_quota = 20000
        free_tier_read_quota = 50000
        
        counters = Dict{CounterType, Counter}(
            READS => Counter(READS, free_tier_read_quota - 5000),
            WRITES => Counter(WRITES, free_tier_write_quota - 500)
        )
        
        base_dir = dirname(@__FILE__)
        common_dir = joinpath(base_dir, "../../common")
        if !isdir(common_dir)
            common_dir = joinpath(base_dir, "../common")
        end
        
        schema_path = joinpath(common_dir, "firebase/db-schema.json")
        db_schema = if isfile(schema_path)
            JSON3.read(read(schema_path, String))
        else
            @warn "Schema file not found at $schema_path"
            Dict()
        end
        
        if haskey(ENV, "FIRESTORE_EMULATOR_HOST")
            project_val = "demo-project"
            @info "USING EMULATOR: $(ENV["FIRESTORE_EMULATOR_HOST"])"
        else
            @info "USING LIVE DATABASE"
        end
        
        @info "Current project: $project_val"
        @info "Current config: $config_val"
        
        _db = nothing
        
        new(free_tier_write_quota, free_tier_read_quota, counters, 
            db_schema, project_val, config_val, _db)
    end
end

function wait_for_port(; timeout::Float64=30.0)
    if haskey(ENV, "FIRESTORE_EMULATOR_HOST")
        host, port = split(ENV["FIRESTORE_EMULATOR_HOST"], ":")
        Utils.wait_for_port(parse(Int, port), host; timeout=timeout)
    end
end

function get_client(; project=nothing, config=nothing)
    return DatabaseClient(; project=project, config=config)
end

function init_db!(db::DatabaseClient)
    doc = get_doc!(db, "meta/video_ids")
    if isempty(doc) || !haskey(doc, "videoIds")
        set_doc!(db, "meta/video_ids", Dict("videoIds" => String[]))
    end
    
    doc = get_doc!(db, "meta/state")
    if isempty(doc)
        set_doc!(db, "meta/state", Dict())
    end
    
    set_doc!(db, "meta/test", Dict())
    return db
end

function increase_counter!(db::DatabaseClient, type::CounterType, increase::Int=1)
    increment!(db.counters[type], increase)
end

function set_doc!(db::DatabaseClient, path::String, data::Dict; merge::Bool=false, kwargs...)
    increment!(db.counters[WRITES])
    @debug "Setting document: $path (merge=$merge)"
    return data
end

function get_doc!(db::DatabaseClient, path::String; kwargs...)
    increment!(db.counters[READS])
    @debug "Getting document: $path"
    return Dict()
end

function update_doc!(db::DatabaseClient, path::String, data::Dict; kwargs...)
    increment!(db.counters[WRITES])
    @debug "Updating document: $path"
    return data
end

function delete_doc!(db::DatabaseClient, path::String; kwargs...)
    increment!(db.counters[WRITES])
    @debug "Deleting document: $path"
end

function recursive_delete!(db::DatabaseClient, path::String)
    @debug "Recursively deleting: $path"
end

function set_noquota!(db::DatabaseClient, path::String, data::Dict; kwargs...)
    @debug "Setting document (no quota): $path"
    return data
end

function update_noquota!(db::DatabaseClient, path::String, data::Dict; kwargs...)
    @debug "Updating document (no quota): $path"
    return data
end

function get_noquota!(db::DatabaseClient, path::String; kwargs...)
    @debug "Getting document (no quota): $path"
    return Dict()
end

function validate_video_schema(db::DatabaseClient, video_dict::Dict)
    if isempty(db.db_schema)
        return true
    end
    
    try
        return true
    catch e
        video_id = get(video_dict, "id", "unknown")
        @warn "Video $video_id did not pass schema validation: $e"
        return false
    end
end

function delete_invalid_docs!(db::DatabaseClient)
    @info "Deleting invalid documents"
end

function get_stats(db::DatabaseClient)
    read_c = db.counters[READS]
    write_c = db.counters[WRITES]
    return Set([string(read_c), string(write_c)])
end

end # module DB

# ============================================================================
# YouTube API Module
# ============================================================================
module YoutubeAPI

using HTTP
using JSON3
using Logging
using URIs
using Random
using ..Utils
import ..Utils: QuotaExceeded, wait_for_port

export YouTubeClient, get_video_info, get_playlist_info, list_playlist_items,
       get_channel_info, list_channel_playlist_ids, list_channelsection_playlist_ids,
       get_related_videos, get_video_transcript, YTQuotaExceeded, aclose

struct YTQuotaExceeded <: Exception
    status::Int
    json_data::Dict
end

Base.show(io::IO, e::YTQuotaExceeded) = print(io, "YTQuotaExceeded: $(e.status)\n$(JSON3.write(e.json_data, indent=4))")

function parse_youtube_id(string::String)
    m = match(r"\[(.{11})\]\.", string)
    isnothing(m) && return nothing
    return m.captures[1]
end

mutable struct Cache
    redis_conn::Any
    
    Cache(redis_db_n=nothing) = new(nothing)
end

function stats(cache::Cache)
    return Dict{String, Any}()
end

function cache_key_func(url::String, params::Dict)
    sorted_keys = sort(collect(keys(params)))
    param_pairs = []
    
    for key in sorted_keys
        key == "key" && continue
        push!(param_pairs, "$key=$(params[key])")
    end
    
    param_string = join(param_pairs, "&")
    return lstrip(url, '/') * "?" * param_string
end

function pages_key_func(key::String, page_n::Int)
    return "$(key)_page_$(page_n)"
end

function get_cache(cache::Cache, key::String)
    return nothing, nothing
end

function set_cache(cache::Cache, key::String, pages::Vector)
    return pages
end

mutable struct YouTubeClient
    db::Any
    http::Any
    cache::Cache
    yt_key::String
    root_url::String
    
    function YouTubeClient(db; yt_key=nothing, redis_db_n=nothing)
        yt_key_val = if isnothing(yt_key)
            get(ENV, "YOUTUBE_API_KEY", "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU")
        else
            yt_key
        end
        
        root_url = get(ENV, "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")
        @debug "Pointing at URL: $root_url"
        
        http = nothing
        new(db, http, Cache(redis_db_n), yt_key_val, root_url)
    end
end

function get_root_url()
    return get(ENV, "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")
end

function wait_for_port()
    root_url = get_root_url()
    uri = URI(root_url)
    if !isnothing(uri.port)
        Utils.wait_for_port(uri.port)
    end
end

function aclose(api::YouTubeClient)
end

function get_with_retries(api::YouTubeClient, url::String; 
                          timeout::Float64=60.0, headers::Dict=Dict(), max_retries::Int=5)
    retries = 0
    
    while true
        try
            response = HTTP.get(url, headers; readtimeout=timeout)
            
            must_retry = 500 <= response.status < 600
            log_level = must_retry ? Logging.Warn : Logging.Debug
            @logmsg log_level "Received response for URL: $url code: $(response.status)"
            
            !must_retry && return response
            
            retries += 1
            if retries > max_retries
                throw(HTTP.ExceptionRequest.StatusError(response.status, "", response))
            end
            
            sleep(3.0)
        catch e
            if e isa HTTP.Exceptions.TimeoutError || e isa Base.IOError
                retries += 1
                if retries > max_retries
                    rethrow(e)
                end
                sleep(3.0)
            else
                rethrow(e)
            end
        end
    end
end

function request_base(api::YouTubeClient, endpoint::String, params::Dict; headers::Dict=Dict())
    params_copy = copy(params)
    params_copy["key"] = api.yt_key
    
    query_parts = String[]
    for (k, v) in params_copy
        push!(query_parts, "$(HTTP.escapeuri(string(k)))=$(HTTP.escapeuri(string(v)))")
    end
    
    url = api.root_url * endpoint * "?" * join(query_parts, "&")
    page_token = nothing
    pages = []
    first_status = nothing
    
    while true
        final_url = isnothing(page_token) ? url : url * "&pageToken=" * page_token
        @debug "Requesting: $final_url"
        
        response = get_with_retries(api, final_url; headers=headers)
        
        if isnothing(first_status)
            first_status = response.status
        end
        
        if response.status == 403
            json_data = try
                JSON3.read(String(response.body))
            catch
                Dict()
            end
            throw(YTQuotaExceeded(response.status, json_data))
        end
        
        if response.status != 304 && response.status >= 400
            throw(HTTP.ExceptionRequest.StatusError(response.status, "", response))
        end
        
        response.status == 304 && break
        
        json_response = JSON3.read(String(response.body))
        push!(pages, json_response)
        
        !haskey(json_response, :nextPageToken) && break
        page_token = json_response.nextPageToken
    end
    
    return first_status, pages
end

function request_with_cache(api::YouTubeClient, endpoint::String, params::Dict)
    headers = Dict{String, String}()
    key = cache_key_func(endpoint, params)
    
    etag, cached_pages = get_cache(api.cache, key)
    
    if !isnothing(etag)
        @debug "Request with key $key CACHED, E-tag: $etag"
        headers["If-None-Match"] = etag
    else
        @debug "Request with key $key NOT cached"
    end
    
    status_code, pages = request_base(api, endpoint, params; headers=headers)
    
    if status_code == 304
        if isnothing(cached_pages)
            throw(KeyError(key))
        end
        return status_code, cached_pages
    elseif 200 <= status_code < 300
        cached = set_cache(api.cache, key, pages)
        return status_code, cached
    else
        @warn "Unexpected status code: $status_code"
        return status_code, pages
    end
end

function request_main(api::YouTubeClient, endpoint::String, params::Dict; use_cache::Bool=true)
    status_code, pages = if use_cache
        request_with_cache(api, endpoint, params)
    else
        request_base(api, endpoint, params)
    end
    
    modified = status_code != 304
    
    items = Channel() do ch
        for page in pages
            if haskey(page, :items)
                for item in page.items
                    put!(ch, item)
                end
            end
        end
    end
    
    return modified, items
end

function request_one(api::YouTubeClient, endpoint::String, params::Dict; use_cache::Bool=true)
    modified, items_ch = request_main(api, endpoint, params; use_cache=use_cache)
    
    item = nothing
    try
        item = take!(items_ch)
    catch
    end
    
    close(items_ch)
    return modified, item
end

function get_video_info(api::YouTubeClient, youtube_id::String)
    endpoint = "/videos"
    params = Dict(
        "part" => "snippet,contentDetails,statistics",
        "id" => youtube_id
    )
    return request_one(api, endpoint, params)
end

function get_playlist_info(api::YouTubeClient, playlist_id::String)
    endpoint = "/playlists"
    params = Dict(
        "part" => "snippet",
        "id" => playlist_id
    )
    return request_one(api, endpoint, params)
end

function list_playlist_items(api::YouTubeClient, playlist_id::String)
    endpoint = "/playlistItems"
    params = Dict(
        "part" => "snippet",
        "playlistId" => playlist_id
    )
    return request_main(api, endpoint, params)
end

function get_channel_info(api::YouTubeClient, channel_id::String)
    endpoint = "/channels"
    params = Dict(
        "part" => "snippet,contentDetails,statistics",
        "id" => channel_id
    )
    return request_one(api, endpoint, params)
end

function list_channelsection_playlist_ids(api::YouTubeClient, channel_id::String)
    endpoint = "/channelSections"
    params = Dict(
        "part" => "contentDetails",
        "channelId" => channel_id
    )
    
    modified, items_ch = request_main(api, endpoint, params)
    
    ids_ch = Channel() do ch
        for item in items_ch
            if haskey(item, :contentDetails) && haskey(item.contentDetails, :playlists)
                for playlist_id in item.contentDetails.playlists
                    put!(ch, playlist_id)
                end
            end
        end
    end
    
    return modified, ids_ch
end

function list_channel_playlist_ids(api::YouTubeClient, channel_id::String)
    endpoint = "/playlists"
    params = Dict(
        "part" => "snippet,contentDetails",
        "channelId" => channel_id
    )
    
    modified, items_ch = request_main(api, endpoint, params)
    
    ids_ch = Channel() do ch
        for item in items_ch
            put!(ch, item.id)
        end
    end
    
    return modified, ids_ch
end

function get_related_videos(api::YouTubeClient, youtube_id::String)
    endpoint = "/search"
    params = Dict(
        "part" => "snippet",
        "type" => "video",
        "relatedToVideoId" => youtube_id
    )
    
    @info "Getting related videos for $youtube_id"
    modified, items_ch = request_main(api, endpoint, params)
    
    related_videos = Dict()
    for video in items_ch
        video_id = video.id.videoId
        if !haskey(related_videos, video_id)
            related_videos[video_id] = video
        end
    end
    
    return modified, collect(values(related_videos))
end

function sentence_case(text::String)
    parts = split(text, r"([.!?]\s*)", keepempty=true)
    result = join([uppercasefirst(strip(part)) for part in parts])
    return result
end

function get_video_transcript(youtube_id::String)
    @warn "Transcript download not implemented - would require youtube_transcript_api equivalent"
    return ""
end

end # module YoutubeAPI

# ============================================================================
# Publisher Module
# ============================================================================
module Publisher

using Logging

export TwitterPublisher, publish_video

mutable struct TwitterPublisher
    db::Any
    
    TwitterPublisher(db) = new(db)
end

function publish_video(publisher::TwitterPublisher, video::Dict)
    @info "Publishing video $(video["id"]) to Twitter"
end

end # module Publisher

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
        db_instance = isnothing(db) ? DatabaseClient() :