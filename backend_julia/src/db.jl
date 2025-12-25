module DB

using Logging
using JSON3
using JSONSchema
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
        # Use JSONSchema.jl to validate
        schema = JSONSchema.Schema(db.db_schema)
        result = JSONSchema.validate(schema, video_dict)
        
        if !isnothing(result)
            video_id = get(video_dict, "id", "unknown")
            @warn "Video $video_id did not pass schema validation: $result"
            return false
        end
        
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