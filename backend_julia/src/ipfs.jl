module VideosDB.IPFS

using Logging
using JSON3
using Sockets
using Dates
using ..Settings: VIDEO_FILES_DIR, IPFS_HOST, IPFS_PORT, VIDEOSDB_DOMAIN, VIDEOSDB_DNSZONE
using ..YoutubeAPI: parse_youtube_id

export DNS, IPFS, parse_youtube_id

struct DNS
    dns_zone::String
end

function DNS(dns_zone::AbstractString)
    return DNS(dns_zone)
end

function _update_record(d::DNS, record_name::AbstractString, record_type::AbstractString, ttl::Int, new_value::AbstractString)
    if isempty(d.dns_zone)
        return nothing
    end
    # Placeholder: in production this should call Google DNS API. For tests we just log.
    @info("DNS update: $record_name $record_type -> $new_value")
    return true
end

function update_dnslink(d::DNS, record_name::AbstractString, new_root_hash::AbstractString)
    return _update_record(d, record_name, "TXT", 300, "dnslink=/ipfs/" * new_root_hash)
end

function update_ip(d::DNS, record_name::AbstractString, new_ip::AbstractString)
    return _update_record(d, record_name, "A", 300, new_ip)
end

mutable struct IPFS
    files_root::String
    files::Dict{String,String}
    dnslink_update_pending::Bool
    host::String
    port::Int
end

function IPFS(files_root::AbstractString = "/videos")
    host = IPFS_HOST
    port = IPFS_PORT
    ip = IPFS(files_root, Dict{String,String}(), false, host, port)
    return ip
end

# Add file: simulate an IPFS add and return a fake hash
function add_file(ip::IPFS, filename::AbstractString; add_to_dir::Bool=true; kwargs...)
    # simple fake hash: hex of timestamp + filename
    h = hex(Int(floor(time())))[end-12:end] * string(abs(hash(filename)))[end-6:end]
    if add_to_dir
        add_to_dir_func(ip, filename, h)
    end
    return h
end

function add_to_dir_func(ip::IPFS, filename::AbstractString, _hash::AbstractString)
    basename = splitpath(filename)[end]
    ip.files[basename] = _hash
    ip.dnslink_update_pending = true
    return true
end

function get_file(ip::IPFS, ipfs_hash::AbstractString)
    # In real client, this would fetch; here return a synthetic filename if present
    for (name,h) in ip.files
        if h == ipfs_hash
            return name
        end
    end
    return nothing
end

function update_dnslink(ip::IPFS; force::Bool=false)
    if !ip.dnslink_update_pending && !force
        return nothing
    end
    # compute a "root_hash" (fake)
    root_hash = join(values(ip.files), ",")
    dns = DNS(VIDEOSDB_DNSZONE)
    update_dnslink(dns, "videos." * VIDEOSDB_DOMAIN, root_hash)
    ip.dnslink_update_pending = false
    return root_hash
end

function _files_in_ipfs_dict(ip::IPFS)
    files_in_ipfs = Dict{String,Any}()
    for (name,h) in ip.files
        if endswith(lowercase(name), ".mp4")
            yid = parse_youtube_id(name)
            if yid === nothing || haskey(files_in_ipfs, yid)
                error("Invalid IPFS state or duplicate")
            end
            files_in_ipfs[yid] = Dict("Name"=>name, "Hash"=>h)
        end
    end
    return files_in_ipfs
end

function _files_in_disk_dict(dir::AbstractString)
    files_in_disk = Dict{String,String}()
    if !isdir(dir)
        return files_in_disk
    end
    for file in readdir(dir)
        if endswith(file, ".part")
            continue
        end
        yid = parse_youtube_id(file)
        if yid === nothing || haskey(files_in_disk, yid)
            error("Invalid disk state or duplicate")
        end
        files_in_disk[yid] = file
    end
    return files_in_disk
end

function download_and_register_folder(ip::IPFS; overwrite_hashes::Bool=false)
    # This is a simplified emulation: check VIDEO_FILES_DIR, compare, and "add" missing files
    videos_dir = abspath(get(ENV, "VIDEO_FILES_DIR", VIDEO_FILES_DIR))
    if !isdir(videos_dir)
        mkpath(videos_dir)
    end
    files_in_ipfs = _files_in_ipfs_dict(ip)
    files_in_disk = _files_in_disk_dict(videos_dir)
    # For the sake of example, add each file from disk to ipfs if missing
    for (yid, file) in files_in_disk
        if haskey(files_in_ipfs, yid)
            continue
        end
        path = joinpath(videos_dir, file)
        h = add_file(ip, path; add_to_dir=true)
        # In real client, update firestore doc; here just log
        @info("Added to IPFS: $file -> $h")
    end
    update_dnslink(ip)
    return true
end

end # module
