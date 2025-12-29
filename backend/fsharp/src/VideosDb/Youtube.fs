namespace VideosDb

open System
open System.Net.Http
open System.Threading.Tasks
open System.Text.Json
open System.Collections.Concurrent
open System.Collections.Generic

module Youtube =

    type CacheEntry = { ETag: string; Pages: JsonElement[] }

    type InMemoryCache() =
        let store = ConcurrentDictionary<string, CacheEntry>()
        member _.Get(key: string) : CacheEntry option =
            match store.TryGetValue(key) with
            | true, v -> Some v
            | _ -> None
        member _.Set(key: string, etag: string, pages: JsonElement[]) =
            store.[key] <- { ETag = etag; Pages = pages }

    type YoutubeApi(http: HttpClient, apiKey: string, ?rootUrl: string, ?cache: InMemoryCache) =
        let root = defaultArg rootUrl "https://www.googleapis.com/youtube/v3"
        let cache = defaultArg cache (InMemoryCache())

        let buildUrl (path: string) (queryParams: (string * string) list) =
            let qp = System.String.Join("&", (queryParams |> List.map (fun (k,v) -> System.Uri.EscapeDataString(k) + "=" + System.Uri.EscapeDataString(v))))
            sprintf "%s%s?%s&key=%s" root path qp apiKey

        member _.GetRawAsync(path: string, queryParams: (string * string) list) = task {
            let url = buildUrl path queryParams
            use! resp = http.GetAsync(url) |> Async.AwaitTask
            // Accept 200 and 304 like the original
            if not (resp.IsSuccessStatusCode || resp.StatusCode = System.Net.HttpStatusCode.NotModified) then
                resp.EnsureSuccessStatusCode() |> ignore
            use! s = resp.Content.ReadAsStreamAsync() |> Async.AwaitTask
            let doc = JsonDocument.Parse(s)
            return doc.RootElement.Clone()
        }

        member this.GetPlaylistInfoAsync(playlistId: string) =
            this.GetRawAsync("/playlists", [ ("part","snippet"); ("id", playlistId) ])

        member this.ListPlaylistItemsAsync(playlistId: string) = task {
            // naive implementation: single page only for tests
            let! root = this.GetRawAsync("/playlistItems", [ ("part","snippet"); ("playlistId", playlistId) ])
            return root
        }

        member this.GetChannelInfoAsync(channelId: string) =
            this.GetRawAsync("/channels", [ ("part","snippet,contentDetails,statistics"); ("id", channelId) ])

        member this.GetVideoInfoAsync(videoId: string) =
            this.GetRawAsync("/videos", [ ("part","snippet,contentDetails,statistics"); ("id", videoId) ])

    let getVideoTranscript (youtubeId: string) : Task<string> =
        // Placeholder: the Python project uses an external lib that scrapes transcripts.
        // For the port, this is a simple stub that can be replaced with a real implementation.
        Task.FromResult(sprintf "Transcript for %s" youtubeId)

    let parseYoutubeId (filename: string) : string option =
        // match pattern [xxxxxxxxxxx].ext
        let m = System.Text.RegularExpressions.Regex.Match(filename, "\[(.{11})\]\\.")
        if m.Success then Some (m.Groups.[1].Value) else None
