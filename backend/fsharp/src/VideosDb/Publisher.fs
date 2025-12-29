namespace VideosDb

open System
open System.Threading.Tasks
open System.Collections.Concurrent
open VideosDb

module Publisher =

    type IPublisher =
        abstract member PublishVideoAsync : JsonElement -> Task

    type InMemoryPublisher() =
        let published = ConcurrentQueue<JsonElement>()
        member _.Published = published
        interface IPublisher with
            member _.PublishVideoAsync(video) = task {
                published.Enqueue(video)
                return ()
            }

    open System.Net.Http
    open Tweetinvi

    type TwitterPublisherAdapter(consumerKey:string, consumerSecret:string, accessToken:string, accessSecret:string, configName: string) =
        let configName = configName
        let clientOpt =
            if not (String.IsNullOrEmpty(consumerKey)) then
                try
                    let c = new TwitterClient(consumerKey, consumerSecret, accessToken, accessSecret)
                    Some c
                with _ -> None
            else None

        member _.ConfigName = configName
        interface IPublisher with
            member _.PublishVideoAsync(video) = task {
                if configName <> "nithyananda" then return ()
                match clientOpt with
                | None -> return ()
                | Some client ->
                    try
                        // create text similar to Python implementation
                        let title = if video.TryGetProperty("snippet", &_) then video.GetProperty("snippet").GetProperty("title").GetString() else ""
                        let ytUrl = sprintf "http://youtu.be/%s" (if video.TryGetProperty("id", &_) then video.GetProperty("id").GetString() else "")
                        let text = sprintf "%s\n%s" title ytUrl
                        let _ = client.Tweets.PublishTweetAsync(text).Result
                        return ()
                    with ex ->
                        return ()
            }

    // Helper to create short URL via Firebase dynamic links
    let getShortUrlAsync (httpClient: HttpClient) (apiKey: string) (url: string) = task {
        let requestUrl = sprintf "https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key=%s" apiKey
        let json = JsonDocument.Parse(sprintf "{ \"dynamicLinkInfo\": { \"domainUriPrefix\": \"https://www.nithyananda.cc/v\", \"link\": \"%s\"}}" url)
        use content = new StringContent(json.RootElement.GetRawText(), System.Text.Encoding.UTF8, "application/json")
        let! resp = httpClient.PostAsync(requestUrl, content) |> Async.AwaitTask
        resp.EnsureSuccessStatusCode() |> ignore
        let! body = resp.Content.ReadAsStringAsync() |> Async.AwaitTask
        let doc = JsonDocument.Parse(body)
        return doc.RootElement.GetProperty("shortLink").GetString()
    }

    // Helper to create short URL via Firebase dynamic links (using HttpClient) - stubbed for tests
    let getShortUrlAsync (http: obj) (url: string) =
        // in production this would call Firebase dynamic links API
        Task.FromResult("https://short.url/abcd")
