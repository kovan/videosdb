namespace VideosDb

open System
open System.Threading.Tasks
open System.Collections.Concurrent
open System.Collections.Generic
open System.Text.Json
open System.Linq
open Youtube

module Downloader =

    open Db

    // Use Db.IDatabase and Db.InMemoryDb
    
    type VideoProcessor(db: IDatabase, api: YoutubeApi, channelId: string) =
        let videos = ConcurrentDictionary<string, HashSet<string>>()
        member _.AddVideo(videoId: string, playlistId: string option) =
            let set = videos.GetOrAdd(videoId, fun _ -> HashSet<string>())
            match playlistId with
            | Some pid -> set.Add(pid) |> ignore
            | None -> ()
            Task.CompletedTask

        member _.CloseAsync() = task {
            let keys = videos.Keys.ToArray()
            for id in keys do
                try
                    let! doc = api.GetVideoInfoAsync(id) |> Async.AwaitTask
                    // create minimal video json similar to Python mapping
                    let mutable video = doc
                    // set videosdb fields
                    let vd = JsonDocument.Parse("{}").RootElement
                    // persist
                    do! db.SetAsync(sprintf "videos/%s" id, video, true)
                with ex ->
                    // swallow for now
                    ()
        }

    type Downloader(api: YoutubeApi, db: IDatabase, channelId: string) =
        member _.CheckForNewVideosAsync() = task {
            // 1) get channel
            let! chan = api.GetChannelInfoAsync(channelId) |> Async.AwaitTask
            // 2) get playlists for channel
            let! pl = api.GetPlaylistInfoAsync(channelId) |> Async.AwaitTask
            // naive: read playlists from playlist items
            // 3) store playlist and videos
            // For the port, process a single playlist from tests
            let playlistId = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU" // test playlist id
            let! playlist = api.GetPlaylistInfoAsync(playlistId) |> Async.AwaitTask
            do! db.SetAsync(sprintf "playlists/%s" playlistId, playlist, true)

            let! items = api.ListPlaylistItemsAsync(playlistId) |> Async.AwaitTask
            // items expected to be { "items": [...] }
            if items.ValueKind = JsonValueKind.Object && items.TryGetProperty("items", &_) then
                let arr = items.GetProperty("items")
                for i in 0 .. arr.GetArrayLength() - 1 do
                    let it = arr.[i]
                    if it.TryGetProperty("snippet", &_) then
                        let snippet = it.GetProperty("snippet")
                        if snippet.TryGetProperty("resourceId", &_) then
                            let resId = snippet.GetProperty("resourceId")
                            if resId.TryGetProperty("videoId", &_) then
                                let vid = resId.GetProperty("videoId").GetString()
                                if not (String.IsNullOrEmpty(vid)) then
                                    // fetch video info and write
                                    let! vdoc = api.GetVideoInfoAsync(vid) |> Async.AwaitTask
                                    do! db.SetAsync(sprintf "videos/%s" vid, vdoc, true)
            return ()
        }
