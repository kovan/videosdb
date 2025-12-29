namespace VideosDb

open System
open System.IO
open System.Collections.Concurrent
open System.Collections.Generic
open System.Threading.Tasks
open VideosDb

module Ipfs =

    type FileInfo = { Name: string; Hash: string; Size: int64 }

    type IIpfs =
        abstract member AddFileAsync : string * bool -> Task<string>
        abstract member AddToDirAsync : string * string -> Task
        abstract member GetFileAsync : string -> Task<string>
        abstract member UpdateDnslinkAsync : bool -> Task
        abstract member FilesInIpfsDict : unit -> IDictionary<string, FileInfo>

    type InMemoryIpfs() =
        let files = ConcurrentDictionary<string, FileInfo>()
        let mutable dnslinkPending = false
        member _.DnslinkPending
            with get() = dnslinkPending
            and set(v) = dnslinkPending <- v

        interface IIpfs with
            member _.AddFileAsync(filename, addToDir) = task {
                // simplistic hash: filename reversed + timestamp
                let hash = (Guid.NewGuid().ToString("N")).Substring(0, 10)
                let fi = { Name = Path.GetFileName(filename); Hash = hash; Size = 0L }
                let id = Path.GetFileNameWithoutExtension(filename)
                files.[id] <- fi
                if addToDir then dnslinkPending <- true
                return hash
            }
            member _.AddToDirAsync(filename, _hash) = task {
                let id = Path.GetFileNameWithoutExtension(filename)
                files.[id] <- { Name = Path.GetFileName(filename); Hash = _hash; Size = 0L }
                dnslinkPending <- true
                return ()
            }
            member _.GetFileAsync(ipfsHash) = task {
                // find by hash
                let kv = files |> Seq.tryFind (fun kv -> kv.Value.Hash = ipfsHash)
                match kv with
                | Some kv -> return kv.Value.Name
                | None -> return String.Empty
            }
            member _.UpdateDnslinkAsync(force) = task {
                if not dnslinkPending && not force then return ()
                // simulate DNS update
                dnslinkPending <- false
                return ()
            }
            member _.FilesInIpfsDict() =
                files :> IDictionary<string, FileInfo>

    // Adapter that would use a real Ipfs client in production
    open System.Net.Http
    open System.Text.Json

    type IpfsAdapter(host:string, port:int) =
        let baseUrl = sprintf "http://%s:%d/api/v0" host port
        let http = new HttpClient()

        let parseHashFromAddResponse (s:string) =
            try
                let doc = JsonDocument.Parse(s)
                if doc.RootElement.TryGetProperty("Hash", &_) then
                    doc.RootElement.GetProperty("Hash").GetString()
                else None
            with _ -> None

        member private _.EnsureFilesRootAsync() = task {
            // create dir /videos if not exists
            let! _ = http.PostAsync(sprintf "%s/files/mkdir?arg=%s&parents=true" baseUrl "/videos", null) |> Async.AwaitTask
            return ()
        }

        interface IIpfs with
            member _.AddFileAsync(filename, addToDir) = task {
                use fs = File.OpenRead(filename)
                use content = new MultipartFormDataContent()
                use filecontent = new StreamContent(fs)
                content.Add(filecontent, "file", Path.GetFileName(filename))
                let! resp = http.PostAsync(baseUrl + "/add?pin=true", content) |> Async.AwaitTask
                let! body = resp.Content.ReadAsStringAsync() |> Async.AwaitTask
                match parseHashFromAddResponse(body) with
                | Some h ->
                    if addToDir then do! ( (this :> IIpfs).AddToDirAsync(Path.GetFileName(filename), h) )
                    return h
                | None -> return String.Empty
            }

            member _.AddToDirAsync(filename, _hash) = task {
                // cp from /ipfs/<hash> to /videos/<basename>
                let dst = sprintf "/videos/%s" (Path.GetFileName(filename))
                let! _ = http.PostAsync(sprintf "%s/files/rm?arg=%s" baseUrl dst, null) |> Async.AwaitTask
                let args = sprintf "%s/files/cp?arg=%s&arg=%s" baseUrl (sprintf "/ipfs/%s" _hash) dst
                let! _ = http.PostAsync(args, null) |> Async.AwaitTask
                return ()
            }

            member _.GetFileAsync(ipfsHash) = task {
                // Download file to current dir with /api/v0/get?arg=<hash>
                let! resp = http.PostAsync(sprintf "%s/get?arg=%s" baseUrl ipfsHash, null) |> Async.AwaitTask
                let! bytes = resp.Content.ReadAsByteArrayAsync() |> Async.AwaitTask
                // write to temp file
                let tmp = Path.Combine(Environment.CurrentDirectory, ipfsHash + ".tar")
                File.WriteAllBytes(tmp, bytes)
                return tmp
            }

            member _.UpdateDnslinkAsync(force) = task {
                // update dnslink by calling files/stat to find root hash
                let! statResp = http.PostAsync(sprintf "%s/files/stat?arg=%s" baseUrl "/videos", null) |> Async.AwaitTask
                let! body = statResp.Content.ReadAsStringAsync() |> Async.AwaitTask
                try
                    let doc = JsonDocument.Parse(body)
                    if doc.RootElement.TryGetProperty("Hash", &_) then
                        let root = doc.RootElement.GetProperty("Hash").GetString()
                        // TODO: update Cloud DNS record with this root hash using Google Cloud DNS API
                        return ()
                with _ -> ()
                return ()
            }

            member _.FilesInIpfsDict() =
                // call files/ls and parse entries
                let resp = http.PostAsync(sprintf "%s/files/ls?arg=%s&long=true" baseUrl "/videos", null).Result
                let body = resp.Content.ReadAsStringAsync().Result
                let dict = Dictionary<string, FileInfo>()
                try
                    let doc = JsonDocument.Parse(body)
                    if doc.RootElement.TryGetProperty("Entries", &_) then
                        for e in doc.RootElement.GetProperty("Entries").EnumerateArray() do
                            let name = e.GetProperty("Name").GetString()
                            let h = e.GetProperty("Hash").GetString()
                            dict.[name] <- { Name = name; Hash = h; Size = if e.TryGetProperty("Size", &_) then e.GetProperty("Size").GetInt64() else 0L }
                with _ -> ()
                dict :> IDictionary<string, FileInfo>
