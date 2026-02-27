module VideosDB.DB

using JSON3
using Logging
using Dates

export CounterTypes, Counter, DB, get_client

# Simple counter types
@enum CounterTypes READS WRITES

mutable struct Counter
    type::CounterTypes
    counter::Int
    limit::Int
    lock::ReentrantLock
    function Counter(type::CounterTypes, limit::Int)
        new(type, 0, limit, ReentrantLock())
    end
end

function inc(c::Counter, quantity::Int=1)
    lock(c.lock) do
        c.counter += quantity
        if c.counter > c.limit
            error("QuotaExceeded: Surpassed $(c.type) ops limit of $(c.limit)")
        end
    end
end

# Minimal in-memory DB emulation for tests
mutable struct DB
    FREE_TIER_WRITE_QUOTA::Int
    FREE_TIER_READ_QUOTA::Int
    _counters::Dict{CounterTypes, Counter}
    store::Dict{String, Any}
    db_schema::Any
end

function get_common_dir()
    # The repo layout has a top-level `common` directory.
    # __DIR__ is src/ so go up two levels
    common_dir = normpath(joinpath(@__DIR__, "..", "..", "common"))
    return common_dir
end

function get_client(; project=nothing, config=nothing)
    # For now return a DB instance (emulator-like) for tests
    db = DB(20000, 50000, Dict{CounterTypes, Counter}(), Dict{String,Any}(), nothing)

    db._counters[READS] = Counter(READS, db.FREE_TIER_READ_QUOTA - 5000)
    db._counters[WRITES] = Counter(WRITES, db.FREE_TIER_WRITE_QUOTA - 500)

    # load schema if available
    try
        schema_path = joinpath(get_common_dir(), "firebase", "db-schema.json")
        if isfile(schema_path)
            db.db_schema = JSON3.read(open(schema_path) |> read, JSON3.Object)
        else
            db.db_schema = nothing
        end
    catch e
        @warn "Could not load db schema: $e"
        db.db_schema = nothing
    end

    return db
end

function DB()
    return get_client()
end

# Basic document operations
function set(db::DB, path::AbstractString, value; merge::Bool=false)
    if !merge || !haskey(db.store, path)
        db.store[path] = deepcopy(value)
    else
        # shallow merge
        existing = db.store[path]
        db.store[path] = merge(existing, value)
    end
    inc(db._counters[WRITES])
    return true
end

function set_noquota(db::DB, path::AbstractString, value; merge::Bool=false)
    if !merge || !haskey(db.store, path)
        db.store[path] = deepcopy(value)
    else
        existing = db.store[path]
        db.store[path] = merge(existing, value)
    end
    return true
end

function get(db::DB, path::AbstractString)
    inc(db._counters[READS])
    return get(db.store, path, nothing)
end

function update(db::DB, path::AbstractString, value)
    if !haskey(db.store, path)
        error("Document does not exist: $path")
    end
    db.store[path] = merge(db.store[path], value)
    inc(db._counters[WRITES])
    return true
end

function delete(db::DB, path::AbstractString)
    if haskey(db.store, path)
        delete!(db.store, path)
    end
    inc(db._counters[WRITES])
    return true
end

function recursive_delete(db::DB, path::AbstractString)
    prefix = path * "/"
    keys_to_delete = [k for k in keys(db.store) if startswith(k, prefix) || k == path]
    for k in keys_to_delete
        delete!(db.store, k)
    end
    inc(db._counters[WRITES], length(keys_to_delete))
    return true
end

# simple stats
function get_stats(db::DB)
    return (string(db._counters[READS]), string(db._counters[WRITES]))
end

# simple schema validation placeholder
function validate_video_schema(db::DB, video_dict)
    # If db.db_schema is available we could run a proper validation
    # For now just return true
    return true
end

end # module
