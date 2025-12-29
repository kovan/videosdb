namespace VideosDb

open System
open System.Threading.Tasks
open VideosDb
open Downloader
open Db

module Cli =

    let parseArgs (argv: string[]) =
        let opts = System.Collections.Generic.Dictionary<string, string>()
        for i in 0 .. argv.Length - 1 do
            match argv.[i] with
            | "-c" | "--check-for-new-videos" -> opts.["check"] <- "true"
            | "-s" | "--validate-db-schema" -> opts.["validate"] <- "true"
            | opt when opt.StartsWith("--dotenv=") -> opts.["dotenv"] <- opt.Substring(opt.IndexOf("=")+1)
            | _ -> ()
        opts

    let loadDotenv path =
        if String.IsNullOrEmpty(path) then ()
        else
            try
                for line in System.IO.File.ReadAllLines(path) do
                    let line = line.Trim()
                    if not (String.IsNullOrEmpty(line)) && not (line.StartsWith("#")) then
                        let parts = line.Split('=')
                        if parts.Length >= 2 then
                            Environment.SetEnvironmentVariable(parts.[0].Trim(), String.Join("=", parts.[1..]).Trim())
            with _ -> ()

    let run (argv: string[]) = task {
        let opts = parseArgs argv
        match opts.TryGetValue("dotenv") with
        | true, path -> loadDotenv path
        | _ -> ()

        // choose DB: if FIRESTORE_EMULATOR_HOST is set use FirestoreAdapter (stub) else InMemory for now
        let db : IDatabase =
            match Environment.GetEnvironmentVariable("FIRESTORE_EMULATOR_HOST") with
            | null -> InMemoryDb() :> IDatabase
            | _ -> FirestoreAdapter("demo-project", None) :> IDatabase

        if opts.ContainsKey("check") then
            // create api http client
            use http = new System.Net.Http.HttpClient()
            let api = Youtube.YoutubeApi(http, Environment.GetEnvironmentVariable("YOUTUBE_API_KEY") ?? "dummy")
            let downloader = Downloader(api, db, Environment.GetEnvironmentVariable("YOUTUBE_CHANNEL_ID") ?? "")
            do! downloader.CheckForNewVideosAsync()

        if opts.ContainsKey("validate") then
            // run a dummy validation on meta/videoIds
            let! _ = db.ValidateVideoSchemaAsync(JsonDocument.Parse("{}").RootElement.Clone()) |> Async.AwaitTask
            ()

        return 0
    }
