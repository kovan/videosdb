# ============================================================================
# run.jl - Main entry point script
# ============================================================================

"""
Main entry point for the VideosDB application.
This script handles command-line arguments and orchestrates the download process.
"""
module RunVideosDB

using ArgParse
using Logging
using Dates
include("Downloader.jl")
using DB

# Load environment variables (similar to dotenv in Python)
# In Julia, you might use DotEnv.jl package
function load_dotenv(filepath::String)
    if !isfile(filepath)
        @warn "Dotenv file not found: $filepath"
        return


    end

    for line in eachline(filepath)
        line = strip(line)
        # Skip empty lines and comments
        if isempty(line) || startswith(line, '#')
            continue
        end

        # Parse KEY=VALUE
        m = match(r"^([^=]+)=(.*)$", line)
        if !isnothing(m)
            key = strip(m.captures[1])
            value = strip(m.captures[2])
            # Remove quotes if present
            value = strip(value, ['"', '\''])
            ENV[key] = value
        end
    end
end

"""
Configure logging based on environment variables.
"""
function configure_logging()
    log_level_str = get(ENV, "LOGLEVEL", "INFO")

    log_level = if log_level_str == "DEBUG"
        Logging.Debug
    elseif log_level_str == "INFO"
        Logging.Info
    elseif log_level_str == "WARN"
        Logging.Warn
    elseif log_level_str == "ERROR"
        Logging.Error
    elseif log_level_str == "TRACE"
        Logging.Debug  # Julia doesn't have TRACE, use Debug
    else
        Logging.Info
    end

    logger = ConsoleLogger(stdout, log_level)
    global_logger(logger)

    @info "Logging configured with level: $log_level_str"
end

"""
Parse command line arguments.
"""
function parse_commandline()
    s = ArgParseSettings(
        description="VideosDB - YouTube Channel Database Synchronization Tool",
        version="1.0.0",
        add_version=true
    )

    @add_arg_table! s begin
        "--check-for-new-videos", "-c"
        help = "Check for and download new videos from YouTube channel"
        action = :store_true

        "--enable-transcripts", "-e"
        help = "Enable downloading of video transcripts"
        action = :store_true

        "--fill-related-videos", "-d"
        help = "Fill related videos information"
        action = :store_true

        "--update-dnslink", "-u"
        help = "Update DNS link"
        action = :store_true

        "--dotenv", "-v"
        help = "Path to .env file to load environment variables"
        arg_type = String
        default = nothing

        "--export-to-emulator-host", "-x"
        help = "Export data to Firestore emulator at specified host"
        arg_type = String
        default = nothing

        "--enable-twitter-publishing", "-t"
        help = "Enable publishing videos to Twitter/X"
        action = :store_true

        "--download-and-register-in-ipfs", "-f"
        help = "Download videos and register them in IPFS"
        action = :store_true

        "--validate-db-schema", "-s"
        help = "Validate database schema"
        action = :store_true
    end

    return parse_args(s)
end

"""
Main entry point function.
"""
function main()
    # Parse command line arguments
    args = parse_commandline()

    # Load dotenv file if specified
    if !isnothing(args["dotenv"])
        @info "Loading environment from: $(args["dotenv"])"
        load_dotenv(args["dotenv"])
    end

    # Configure logging
    configure_logging()

    @info "VideosDB Starting..."
    @info "Arguments: $args"

    # Check for new videos
    if args["check-for-new-videos"]
        @info "Checking for new videos..."

        options = Downloader.DownloadOptions(
            enable_transcripts=args["enable-transcripts"],
            enable_twitter_publishing=args["enable-twitter-publishing"],
            export_to_emulator_host=args["export-to-emulator-host"]
        )

        downloader = Downloader.VideoDownloader(options=options)

        try
            Downloader.check_for_new_videos!(downloader)
            @info "Video check completed successfully"
        catch e
            @error "Error during video check" exception = (e, catch_backtrace())
            rethrow(e)
        end
    end

    # Validate database schema
    if args["validate-db-schema"]
        @info "Validating database schema..."

        db = DB.DatabaseClient()
        DB.init_db!(db)

        try
            DB.delete_invalid_docs!(db)
            @info "Schema validation completed successfully"
        catch e
            @error "Error during schema validation" exception = (e, catch_backtrace())
            rethrow(e)
        end
    end

    # Fill related videos
    if args["fill-related-videos"]
        @warn "Fill related videos not yet implemented"
        # This would require additional implementation
    end

    # Update DNS link
    if args["update-dnslink"]
        @warn "Update DNS link not yet implemented"
        # This would require additional implementation
    end

    # Download and register in IPFS
    if args["download-and-register-in-ipfs"]
        @warn "Download and register in IPFS not yet implemented"
        # This would require additional implementation
    end

    @info "VideosDB Finished"
end

"""
Entry point when script is run directly.
"""
function entrypoint()
    try
        main()
    catch e
        @error "Fatal error" exception = (e, catch_backtrace())
        exit(1)
    end
end

end # module RunVideosDB

# # Run if this is the main script
# if abspath(PROGRAM_FILE) == @__FILE__
RunVideosDB.entrypoint()
# end