namespace VideosDb

open System
open System.Threading.Tasks
open System.Collections.Concurrent
open System.Text.Json

module Db =

    type IDatabase =
        abstract member SetAsync : string * JsonElement * bool -> Task
        abstract member GetAsync : string -> Task<JsonElement option>
        abstract member InitAsync : unit -> Task
        abstract member ValidateVideoSchemaAsync : JsonElement -> Task<bool>

    type InMemoryDb() =
        let store = ConcurrentDictionary<string, JsonElement>()
        interface IDatabase with
            member _.SetAsync(path, value, merge) =
                store.[path] <- value
                Task.CompletedTask
            member _.GetAsync(path) =
                match store.TryGetValue(path) with
                | true, v -> Task.FromResult(Some v)
                | _ -> Task.FromResult(None)
            member _.InitAsync() = Task.CompletedTask
            member _.ValidateVideoSchemaAsync(_video) = Task.FromResult(true)

    open Google.Cloud.Firestore
    open System.Text.Json
    open System.Collections.Generic

    // Firestore adapter using Google.Cloud.Firestore
    type FirestoreAdapter(projectId: string, ?credsPath: string) =
        let project =
            match Environment.GetEnvironmentVariable("FIRESTORE_PROJECT") with
            | null -> projectId
            | v -> v

        // If GOOGLE_APPLICATION_CREDENTIALS env var supplied, Firestore client will pick it up automatically.
        let db = FirestoreDb.Create(project)

        let rec jsonToObj (el: JsonElement) : obj =
            match el.ValueKind with
            | JsonValueKind.Object ->
                let d = Dictionary<string, obj>()
                for p in el.EnumerateObject() do
                    d.[p.Name] <- jsonToObj p.Value
                d :> obj
            | JsonValueKind.Array ->
                el.EnumerateArray() |> Seq.map jsonToObj |> Seq.toArray :> obj
            | JsonValueKind.String -> el.GetString() :> obj
            | JsonValueKind.Number ->
                match el.TryGetInt64() with
                | true, v -> box v
                | _ ->
                    match el.TryGetDouble() with
                    | true, d -> box d
                    | _ -> null
            | JsonValueKind.True -> box true
            | JsonValueKind.False -> box false
            | _ -> null

        let objToJsonElement (o: obj) =
            let s = JsonSerializer.Serialize(o)
            JsonDocument.Parse(s).RootElement.Clone()

        interface IDatabase with
            member _.SetAsync(path, value, merge) = task {
                let doc = db.Document(path)
                let payload = jsonToObj value
                if merge then
                    let opts = SetOptions.MergeAll
                    do! doc.SetAsync(payload, opts) |> Async.AwaitTask
                else
                    do! doc.SetAsync(payload) |> Async.AwaitTask
            }

            member _.GetAsync(path) = task {
                let doc = db.Document(path)
                let! snap = doc.GetSnapshotAsync() |> Async.AwaitTask
                if not snap.Exists then return None
                else
                    // convert to dict then to json
                    let dict = snap.ToDictionary()
                    let json = JsonSerializer.Serialize(dict)
                    return Some(JsonDocument.Parse(json).RootElement.Clone())
            }

            member _.InitAsync() = task {
                // ensure meta docs exist similar to the Python version
                let vdoc = db.Document("meta/video_ids")
                let! snap = vdoc.GetSnapshotAsync() |> Async.AwaitTask
                if not snap.Exists then
                    do! vdoc.SetAsync(dict<string,obj>([ ("videoIds", box (List<string>())) ])) |> Async.AwaitTask

                let sdoc = db.Document("meta/state")
                let! ss = sdoc.GetSnapshotAsync() |> Async.AwaitTask
                if not ss.Exists then
                    do! sdoc.SetAsync(dict<string,obj>()) |> Async.AwaitTask
            }

            member _.ValidateVideoSchemaAsync(_video) = task {
                // For now rely on tests; full jsonschema validation can be added with NJsonSchema
                return true
            }
