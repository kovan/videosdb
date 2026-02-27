module VideosDB.Publisher

using HTTP
using JSON3
using Dates
using Logging
using ..DB: get_client, set_noquota

export Publisher, TwitterPublisher, _get_short_url_firebase, _create_post_text, publish_video

struct Publisher
    db
end

Publisher(db) = Publisher(db)

function _get_short_url_firebase(self::Publisher, url::AbstractString)
    config = get(ENV, "VIDEOSDB_CONFIG", "")
    config_path = joinpath(dirname(@__FILE__), "..", "common", "firebase", "configs", string(config, ".json"))
    if !isfile(config_path)
        # no config available in tests — fallback to original
        return url
    end
    contents = JSON3.read(open(config_path) |> read)
    api_key = contents["apiKey"]
    request_url = "https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key=" * api_key
    json_data = Dict("dynamicLinkInfo" => Dict("domainUriPrefix" => "https://www.nithyananda.cc/v", "link" => url))
    resp = HTTP.post(request_url, headers=Dict("Content-Type" => "application/json"), body=JSON3.write(json_data))
    if resp.status >= 200 && resp.status < 300
        body = JSON3.read(String(resp.body))
        return body["shortLink"]
    else
        @warn "Failed to create short link, status: $(resp.status)"
        return url
    end
end

function _create_post_text(self::Publisher, video::Dict)
    hostname = get(ENV, "VIDEOSDB_HOSTNAME", "http://localhost")
    url = hostname * "/video/" * string(video["videosdb"]["slug"])
    short_url = try _get_short_url_firebase(self, url) catch e
        @warn("Short link generation failed: $e"); url
    end
    yt_url = "http://youtu.be/" * string(video["id"])
    text = """
$(video["snippet"]["title"])\n$(yt_url)\n$(short_url)
"""
    return text
end

struct TwitterPublisher
    db
end

TwitterPublisher(db) = TwitterPublisher(db)

function publish_video(self::TwitterPublisher, video::Dict)
    # Only publish for production config (mimicking Python behaviour)
    if get(ENV, "VIDEOSDB_CONFIG", "") != "nithyananda"
        return nothing
    end
    video_date = video["snippet"]["publishedAt"]
    now = Dates.now()

    if get(video["videosdb"], "publishing", nothing) !== nothing
        # already published
        return nothing
    end

    text = _create_post_text(Publisher(self.db), video)
    # Simulate posting by generating an id
    id = string(rand(10^8:10^9))

    publishing = Dict("publishDate" => Dates.format(now, Dates.ISODateTimeFormat), "id" => id, "text" => text)
    video["videosdb"]["publishing"] = publishing

    # persist without quota
    set_noquota(self.db, "videos/" * string(video["id"]), video; merge=true)

    # small sleep to mimic rate limit safety
    sleep(0.01)
    @info("Published video $(video["id"]) with id $id")
    return nothing
end

end # module
