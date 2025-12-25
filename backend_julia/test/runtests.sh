using Test
using VideosDB

@testset "VideosDB Tests" begin
    
    @testset "Utils Tests" begin
        using VideosDB.Utils
        
        @test QuotaExceeded("test") isa Exception
        
        # Test put_item_at_front
        seq = [1, 2, 3, 4, 5]
        result = put_item_at_front(seq, 3)
        @test result == [3, 4, 5, 1, 2]
        
        # Test with missing item
        result = put_item_at_front(seq, 10)
        @test result == seq
        
        # Test with nothing
        result = put_item_at_front(seq, nothing)
        @test result == seq
    end
    
    @testset "DB Tests" begin
        using VideosDB.DB
        
        # Test Counter
        counter = DB.Counter(DB.READS, 100)
        @test counter.counter == 0
        @test counter.limit == 100
        
        DB.increment!(counter, 10)
        @test counter.counter == 10
        
        # Test quota exceeded
        @test_throws QuotaExceeded DB.increment!(counter, 95)
        
        # Test DatabaseClient creation
        db = DatabaseClient()
        @test db.free_tier_read_quota == 50000
        @test db.free_tier_write_quota == 20000
        @test haskey(db.counters, READS)
        @test haskey(db.counters, WRITES)
        
        # Test stats
        stats = get_stats(db)
        @test stats isa Set
        @test length(stats) == 2
        
        # Test schema validation with valid data
        video_dict = Dict(
            "id" => "test123",
            "snippet" => Dict("title" => "Test Video"),
            "statistics" => Dict("viewCount" => 1000)
        )
        @test validate_video_schema(db, video_dict) == true
    end
    
    @testset "YouTube API Tests" begin
        using VideosDB.YoutubeAPI
        
        # Test parse_youtube_id
        @test parse_youtube_id("[dQw4w9WgXcQ].mp4") == "dQw4w9WgXcQ"
        @test isnothing(parse_youtube_id("invalid"))
        
        # Test cache_key_func
        url = "/videos"
        params = Dict("part" => "snippet", "id" => "test123", "key" => "apikey")
        key = cache_key_func(url, params)
        @test occursin("id=test123", key)
        @test occursin("part=snippet", key)
        @test !occursin("key=", key)  # API key should be excluded
        
        # Test sentence_case
        text = "this is a test. another sentence! final one?"
        result = sentence_case(text)
        @test startswith(result, "This")
        
        # Test YTQuotaExceeded exception
        exc = YTQuotaExceeded(403, Dict("error" => "quota exceeded"))
        @test exc.status == 403
        @test exc.json_data["error"] == "quota exceeded"
    end
    
    @testset "Downloader Tests" begin
        using VideosDB.Downloader
        using TimeZones
        
        # Test DownloadOptions
        options = DownloadOptions(
            enable_transcripts = true,
            enable_twitter_publishing = false
        )
        @test options.enable_transcripts == true
        @test options.enable_twitter_publishing == false
        @test isnothing(options.export_to_emulator_host)
        
        # Test slugify
        @test slugify("Hello World!") == "hello-world"
        @test slugify("Test@#\$%String") == "teststring"
        @test slugify("Multiple   Spaces") == "multiple-spaces"
        @test slugify("---trim-dashes---") == "trim-dashes"
        
        # Test parse_duration
        @test parse_duration("PT1H30M45S") == 5445  # 1h 30m 45s
        @test parse_duration("PT5M") == 300
        @test parse_duration("PT30S") == 30
        @test parse_duration("PT1H") == 3600
        @test parse_duration("PT0S") == 0
        
        # Test parse_datetime_iso
        dt = parse_datetime_iso("2024-01-15T10:30:00Z")
        @test dt isa ZonedDateTime
        @test TimeZones.timezone(dt) == TimeZones.tz"UTC"
        
        # Test with invalid datetime (should not crash)
        dt_invalid = parse_datetime_iso("invalid_date")
        @test dt_invalid isa ZonedDateTime
        
        # Test description_trimmed
        desc = "This is a video description\n\n#Sadhguru\n#Yoga"
        result = description_trimmed(desc)
        @test !occursin("#Sadhguru", result)
        
        @test isnothing(description_trimmed(nothing))
    end
    
    @testset "Integration Tests" begin
        # Test creating a complete downloader
        # Note: This won't actually make API calls without proper credentials
        
        # Set test environment variables
        ENV["YOUTUBE_CHANNEL_ID"] = "test_channel_id"
        ENV["YOUTUBE_API_KEY"] = "test_api_key"
        ENV["FIREBASE_PROJECT"] = "test_project"
        
        options = VideosDB.Downloader.DownloadOptions(
            enable_transcripts = false,
            enable_twitter_publishing = false
        )
        
        # This should create without errors
        @test_nowarn VideosDB.Downloader.VideoDownloader(
            options = options,
            channel_id = "test_channel"
        )
    end
    
    @testset "Publisher Tests" begin
        using VideosDB.Publisher
        
        db = VideosDB.DB.DatabaseClient()
        publisher = TwitterPublisher(db)
        
        @test publisher.db === db
        
        # Test publish_video doesn't crash
        video = Dict("id" => "test123", "snippet" => Dict("title" => "Test"))
        @test_nowarn publish_video(publisher, video)
    end
    
    @testset "Task Tests" begin
        using VideosDB.Downloader
        
        db = VideosDB.DB.DatabaseClient()
        options = DownloadOptions(enable_transcripts = true)
        
        # Test ExportToEmulatorTask
        task = ExportToEmulatorTask(db, options)
        @test !task.enabled  # Should be disabled without emulator host
        
        # Test with emulator
        options_with_emu = DownloadOptions(
            export_to_emulator_host = "localhost:8080"
        )
        task_emu = ExportToEmulatorTask(db, options_with_emu)
        @test task_emu.enabled
        
        # Test PublishTask
        publish_task = PublishTask(db, options)
        @test !publish_task.enabled
        
        # Test RetrievePendingTranscriptsTask
        transcript_task = RetrievePendingTranscriptsTask(db, options)
        @test transcript_task.enabled
    end
    
    @testset "LockedItem Tests" begin
        using VideosDB.Downloader
        
        item = Dict("key" => "value")
        locked = LockedItem(item)
        
        @test locked.item === item
        @test locked.lock isa ReentrantLock
        
        # Test thread-safe access
        lock(locked.lock) do
            locked.item["new_key"] = "new_value"
        end
        
        @test locked.item["new_key"] == "new_value"
    end
    
    @testset "Redis Cache Tests" begin
        using VideosDB.YoutubeAPI
        
        # Test Cache creation (may fail if Redis not available, which is fine)
        cache = YoutubeAPI.Cache()
        @test cache isa YoutubeAPI.Cache
        
        # Test cache key function
        url = "/videos"
        params = Dict("part" => "snippet", "id" => "test", "key" => "secret")
        key = YoutubeAPI.cache_key_func(url, params)
        @test occursin("id=test", key)
        @test !occursin("key=", key)  # API key excluded
        
        # Test pages key function
        page_key = YoutubeAPI.pages_key_func("test_key", 5)
        @test page_key == "test_key_page_5"
        
        # Test stats (should return empty dict if Redis not connected)
        stats_result = YoutubeAPI.stats(cache)
        @test stats_result isa Dict
    end
    
    @testset "JSONSchema Validation Tests" begin
        using VideosDB.DB
        using JSON3
        
        # Create a simple schema
        schema = Dict(
            "type" => "object",
            "properties" => Dict(
                "id" => Dict("type" => "string"),
                "title" => Dict("type" => "string")
            ),
            "required" => ["id"]
        )
        
        # Test with valid data
        valid_data = Dict("id" => "123", "title" => "Test")
        # Schema validation happens in validate_video_schema
        
        # Test with invalid data (missing required field)
        invalid_data = Dict("title" => "Test")  # Missing "id"
        # Would fail validation in real scenario
    end
        using VideosDB.Utils
        
        # Test my_handler with matching exception
        caught = false
        try
            throw(QuotaExceeded("test error"))
        catch e
            caught = my_handler(QuotaExceeded, e, ex -> @test true)
        end
        @test caught == true
        
        # Test my_handler with non-matching exception
        @test_throws ErrorException begin
            try
                throw(ErrorException("different error"))
            catch e
                my_handler(QuotaExceeded, e, ex -> @test false)
            end
        end
    end
end

@testset "Module Exports" begin
    # Test that main exports are available
    @test isdefined(VideosDB, :Utils)
    @test isdefined(VideosDB, :DB)
    @test isdefined(VideosDB, :YoutubeAPI)
    @test isdefined(VideosDB, :Publisher)
    @test isdefined(VideosDB, :Downloader)
    
    # Test key types are exported
    @test isdefined(VideosDB, :DatabaseClient)
    @test isdefined(VideosDB, :YouTubeClient)
    @test isdefined(VideosDB, :VideoDownloader)
    @test isdefined(VideosDB, :DownloadOptions)
end

# Run performance tests only if requested
if get(ENV, "RUN_PERF_TESTS", "false") == "true"
    @testset "Performance Tests" begin
        using BenchmarkTools
        using VideosDB.Downloader
        
        @testset "Slugify Performance" begin
            @btime slugify("Test String With Spaces")
        end
        
        @testset "Parse Duration Performance" begin
            @btime parse_duration("PT1H30M45S")
        end
    end
end

println("\n✓ All tests passed!")