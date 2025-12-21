module VideosDB.Utils

using Sockets
using Base: @error

export QuotaExceeded, get_module_path, wait_for_port, my_handler, put_item_at_front

struct QuotaExceeded <: Exception
    msg::String
end
Base.showerror(io::IO, e::QuotaExceeded) = print(io, e.msg)

get_module_path() = dirname(@__FILE__)

function wait_for_port(port::Integer; host::AbstractString = "localhost", timeout::Real = 30.0)
    start = time()
    while true
        try
            sock = connect(host, port)
            close(sock)
            return true
        catch e
            sleep(0.01)
            if time() - start >= timeout
                throw(TimeoutError("Waited too long for the port $port on host $host to start accepting connections."))
            end
        end
    end
end

function my_handler(my_type::Type{<:Exception}, e::Exception, handler::Function)
    if isa(e, my_type)
        handler(e)
        return true
    else
        rethrow(e)
    end
end

function put_item_at_front(seq::AbstractVector, item)
    if item === nothing || item == ""
        return copy(seq)
    end
    try
        i = findfirst(x -> x == item, seq)
        if i !== nothing
            n = length(seq)
            return vcat(seq[i:end], seq[1:i-1])
        else
            return copy(seq)
        end
    catch
        return copy(seq)
    end
end

end # module
