namespace VideosDb.Tests

open System
open Xunit
open System.Net.Http
open System.Text.Json
open RichardSzalay.MockHttp
open VideosDb
open Downloader
open System.Threading.Tasks

module DownloaderTests =

    let readJson file =
        let baseDir = __SOURCE_DIRECTORY__ + "/../../../../backend/tests/test_data"
        let txt = System.IO.File.ReadAllText(System.IO.Path.Combine(baseDir, file))
        JsonDocument.Parse(txt).RootElement.Clone()

    [<Fact>]
    let ``process playlist writes playlist and videos`` () =
        use mock = new MockHttpMessageHandler()
        let root = Youtube.YoutubeApi(null, "dummy") // placeholder, will replace HttpClient

        // create mock client and setup endpoints
        let client = mock.ToHttpClient()
        client.BaseAddress <- Uri(Youtube.YoutubeApi(null, "").GetType().Assembly.Location)

        // Setup playlist endpoints
        let playlistJson = readJson "playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json"
        mock.When("https://www.googleapis.com/youtube/v3/playlists*")
            .Respond("application/json", playlistJson.GetRawText()) |> ignore

        let playlistItemsJson0 = readJson "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.0.json"
        mock.When("https://www.googleapis.com/youtube/v3/playlistItems*")
            .Respond("application/json", playlistItemsJson0.GetRawText()) |> ignore

        let videoJson = readJson "video-HADeWBBb1so.response.json"
        mock.When("https://www.googleapis.com/youtube/v3/videos*")
            .Respond("application/json", videoJson.GetRawText()) |> ignore

        let api = Youtube.YoutubeApi(client, "dummy")
        let db = Downloader.InMemoryDb() :> IDatabase
        let downloader = Downloader(api, db, "UCcYzLCs3zrQIBVHYA1sK2sw")

        // run
        downloader.CheckForNewVideosAsync().GetAwaiter().GetResult()

        // assert playlist written
        match (db :?> InMemoryDb).GetType().GetField("store", System.Reflection.BindingFlags.NonPublic ||| System.Reflection.BindingFlags.Instance).GetValue(db) with
        | :? System.Collections.Concurrent.ConcurrentDictionary<string, JsonElement> as s ->
            Assert.True(s.ContainsKey("playlists/PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"))
            Assert.True(s.ContainsKey("videos/HADeWBBb1so"))
        | _ -> Assert.True(false)
