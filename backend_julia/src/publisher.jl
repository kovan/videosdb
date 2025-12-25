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
