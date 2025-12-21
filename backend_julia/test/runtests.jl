using Test
using VideosDB.Settings
using VideosDB.Utils
using VideosDB.YoutubeAPI
using VideosDB.DB
using VideosDB.Publisher
using Dates
using VideosDB.IPFS

@testset "utils tests" begin

    @test put_item_at_front([1,2,3,4], 3) == [3,4,1,2]
    @test put_item_at_front(["a","b","c"], "b") == ["b","c","a"]
    @test_throws TimeoutError wait_for_port(65535; host="127.0.0.1", timeout=0.01)

    called = false
    handler(x) = (global called = true)
    ex = QuotaExceeded("boom")
    res = try
        my_handler(QuotaExceeded, ex, handler)
    catch e
        false
    end
    @test called == true
    @test res == true

end

@testset "downloader tests" begin
    db = get_client()
    d = VideosDB.Downloader.Downloader(db=db, channel_id="UCcYzLCs3zrQIBVHYA1sK2sw")
    # test description trimming
    @test _description_trimmed("Hello #Sadhguru more") == "Hello "
    # run a simplified phase1
    _phase1(d)
    # playlists written
    p = get(db, "playlists/PL1")
    @test p["videosdb"]["videoCount"] == 2
    # videos written
    v = get(db, "videos/v1")
    @test v !== nothing
    @test haskey(v["videosdb"], "slug")
end

@testset "youtube_api tests" begin
    @test parse_youtube_id("something[ABCDEFGHIJK].mp4") == "ABCDEFGHIJK"
    c = Cache()
    pages = [Dict("etag"=>"E1","items"=>[Dict("id"=>1)]), Dict("etag"=>"E2","items"=>[Dict("id"=>2)])]
    set(c, "key1", pages)
    etag, cached = get(c, "key1")
    @test etag == "E1"
    @test length(cached) == 2
end

@testset "db tests" begin
    db = get_client()
    @test set(db, "meta/test", Dict("a"=>1)) == true
    @test get(db, "meta/test") == Dict("a"=>1)
    @test update(db, "meta/test", Dict("b"=>2)) == true
    @test get(db, "meta/test") == Dict("a"=>1, "b"=>2)
    @test delete(db, "meta/test") == true
    @test get(db, "meta/test") === nothing
    # recursive delete
    set(db, "col/doc1", Dict("x"=>1))
    set(db, "col/doc2", Dict("x"=>2))
    recursive_delete(db, "col")
    @test get(db, "col/doc1") === nothing
    @test get(db, "col/doc2") === nothing
end

@testset "publisher tests" begin
    db = get_client()
    ENV["VIDEOSDB_CONFIG"] = "nithyananda"
    p = TwitterPublisher(db)
    video = Dict("id" => "vid1",
                 "snippet" => Dict("title" => "Hello", "publishedAt" => Dates.now()),
                 "videosdb" => Dict("slug" => "hello-video"))

    publish_video(p, video)

    doc = get(db, "videos/vid1")
    @test haskey(doc["videosdb"], "publishing")
    pub = doc["videosdb"]["publishing"]
    @test haskey(pub, "id")
    @test haskey(pub, "text")
end

@testset "ipfs tests" begin
    ip = IPFS("test_videos")
    # create a fake .mp4 file with youtube id
    mkpath("test_videos")
    fname = "video_[ABCDEFGHIJK].mp4"
    open(joinpath("test_videos", fname), "w") do io
        write(io, "dummy")
    end
    files = _files_in_disk_dict("test_videos")
    @test haskey(files, "ABCDEFGHIJK")

    h = add_file(ip, joinpath("test_videos", fname))
    @test get_file(ip, h) == fname

    files_ipfs = _files_in_ipfs_dict(ip)
    @test haskey(files_ipfs, "ABCDEFGHIJK")

    root = update_dnslink(ip; force=true)
    @test typeof(root) == String
end
