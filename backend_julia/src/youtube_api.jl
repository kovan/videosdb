module VideosDB.YoutubeAPI

using HTTP
using JSON3
using Dates
using .Settings: YOUTUBE_KEY
using .Utils: wait_for_port

export parse_youtube_id, Cache, YoutubeAPI, get_video_transcript, Cache

import Base: show

function parse_youtube_id(s::AbstractString)
    m = match(r"\[(.{11})]\.", s)
    return m === nothing ? nothing : m.captures[1]
end

mutable struct Cache
    store::Dict{String,Any}
    function Cache()
        new(Dict{String,Any}())
    end
end

function Cache.key_func(url::String, params::Dict{String,Any})
    keys = collect(keys(params))
    sort!(keys)
    params_seq = []
    for k in keys
        if k == "key"
            continue
        end
        push!(params_seq, (k, params[k]))
    end
    final = lstrip(url, '/') * "?" * join(["$(k)=$(v)" for (k,v) in params_seq], "&")
    return final
end

function Cache._pages_key_func(key::String, page_n::Integer)
    return string(key, "_page_", page_n)
end

function get(cache::Cache, key::String)
    if !haskey(cache.store, key)
        return nothing, nothing
    end
    entry = cache.store[key]
    return entry[:etag], entry[:pages]
end

function set(cache::Cache, key::String, pages::Vector{Any})
    etag = isempty(pages) ? nothing : get(pages[1], "etag")
    cache.store[key] = Dict(:etag => etag, :pages => pages)
    return pages
end

struct YTQuotaExceeded <: Exception
    status::Int
    json::Any
end
Base.showerror(io::IO, e::YTQuotaExceeded) = print(io, "YTQuotaExceeded: ", e.status)

mutable struct YoutubeAPI
    yt_key::String
    root_url::String
    cache::Cache
end

function YoutubeAPI(; yt_key::Union{Nothing,String}=nothing)
    k = yt_key === nothing ? get(ENV, "YOUTUBE_API_KEY", YOUTUBE_KEY) : yt_key
    root = get(ENV, "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")
    return YoutubeAPI(k, root, Cache())
end

function get_root_url(::Type{YoutubeAPI})
    return get(ENV, "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")
end

function wait_for_port()
    # If root url has a port, wait for it to be ready
    url = URL(get(ENV, "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3"))
    if !isnothing(url.port)
        wait_for_port(url.port)
    end
end

# -- low level request ----------------------------------------------------

function _get_with_retries(url::String; timeout::Real=60.0, headers=Dict{String,String}(), max_retries::Int=5)
    retries = 0
    while true
        resp = HTTP.get(url; headers=headers)
        status = resp.status
        must_retry = status >= 500 && status < 600
        if !must_retry
            break
        end
        retries += 1
        if retries > max_retries
            error("Too many retries for URL: $url")
        end
        sleep(3.0)
    end
    return resp
end

function _request_base(self::YoutubeAPI, url::String, params::Dict{String,Any}; headers=Dict{String,String}())
    # add key
    params_copy = deepcopy(params)
    params_copy["key"] = self.yt_key
    q = join(["$(k)=$(v)" for (k,v) in pairs(params_copy)], "&")
    full_url = string(self.root_url, url, "?", q)

    pages = Vector{Any}()
    page_token = nothing

    while true
        final_url = page_token === nothing ? full_url : full_url * "&pageToken=" * page_token
        #println("requesting: $final_url")
        resp = _get_with_retries(final_url; headers=headers)
        status = resp.status
        if status == 403
            json_body = try JSON3.read(String(resp.body)) catch _ => nothing end
            throw(YTQuotaExceeded(status, json_body))
        end
        if status != 304 && !(status >= 200 && status < 300)
            error("Unexpected status code: $status")
        end
        if page_token === nothing
            # first yield would be status
            # ignore for now
            nothing
        end
        if status == 304
            break
        end
        json_body = JSON3.read(String(resp.body))
        push!(pages, json_body)
        if !haskey(json_body, "nextPageToken")
            break
        else
            page_token = string(json_body["nextPageToken"])
        end
    end
    return resp.status, pages
end

function _request_with_cache(self::YoutubeAPI, url::String, params::Dict{String,Any})
    headers = Dict{String,String}()
    key = Cache.key_func(url, params)
    etag, cached_pages = get(self.cache, key)
    if etag !== nothing
        headers["If-None-Match"] = string(etag)
    end

    status, response_pages = _request_base(self, url, params; headers=headers)

    if status == 304
        if cached_pages === nothing
            error("Cache miss but got 304")
        end
        return status, cached_pages
    elseif status >= 200 && status < 300
        pages = set(self.cache, key, response_pages)
        return status, pages
    else
        return status, response_pages
    end
end

function _request_main(self::YoutubeAPI, url::String, params::Dict{String,Any}; use_cache::Bool=true)
    if use_cache
        status, pages = _request_with_cache(self, url, params)
    else
        status, pages = _request_base(self, url, params)
    end
    modified = status != 304
    # create an iterator over items
    items = Iterators.flatten((map(p -> get(p, "items", []), pages)))
    return modified, collect(items)
end

function _request_one(self::YoutubeAPI, url::String, params::Dict{String,Any}; use_cache::Bool=true)
    modified, items = _request_main(self, url, params; use_cache=use_cache)
    item = isempty(items) ? nothing : items[1]
    return modified, item
end

# transcript: placeholder implementation
function _sentence_case(text::AbstractString)
    parts = split(text, r"([.!?]\s*)", keepempty=false)
    return join([uppercasefirst(s) for s in parts])
end

function get_video_transcript(youtube_id::AbstractString)
    # Placeholder: a robust implementation would call an external
    # service or use the YouTube transcript API. For now return empty string.
    return ""
end

end # module
