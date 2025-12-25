
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
