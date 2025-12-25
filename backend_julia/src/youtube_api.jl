
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

