namespace VideosDb

module Settings =
    open System

    let private getEnv key defaultValue =
        match Environment.GetEnvironmentVariable(key) with
        | null -> defaultValue
        | v -> v

    let IPFS_HOST : string = getEnv "IPFS_HOST" "127.0.0.1"

    let IPFS_PORT : int =
        match Int32.TryParse(getEnv "IPFS_PORT" "5001") with
        | true, v -> v
        | _ -> 5001

    let VIDEOSDB_DOMAIN : string = getEnv "VIDEOSDB_DOMAIN" "sadhguru.digital"
    let VIDEOSDB_DNSZONE : string = getEnv "VIDEOSDB_DNSZONE" "sadhguru"
    let YOUTUBE_CHANNEL_ID : string = getEnv "YOUTUBE_CHANNEL_ID" "UCcYzLCs3zrQIBVHYA1sK2sw"

module Utils =
    open System
    open System.Net.Sockets
    open System.Threading.Tasks
    open System.IO

    exception QuotaExceeded of string

    let getModulePath () : string =
        let asm = System.Reflection.Assembly.GetExecutingAssembly().Location
        Path.GetDirectoryName(asm)

    let putItemAtFront (sq: seq<string>) (item: string) : seq<string> =
        if String.IsNullOrEmpty(item) then sq
        else
            match Seq.tryFindIndex ((=) item) sq with
            | None -> sq
            | Some i ->
                let arr = Seq.toArray sq
                seq { for x in arr.[i..] do yield x; for x in arr.[0..i-1] do yield x }

    let waitForPortAsync (host:string) (port:int) (timeoutMs:int) : Task =
        let rec loop (start: DateTime) = task {
            try
                use c = new TcpClient()
                let connectTask = c.ConnectAsync(host, port)
                let! completed = Task.WhenAny(connectTask, Task.Delay(timeoutMs)) |> Async.AwaitTask
                if completed = (connectTask :> Task) then
                    return ()
                else
                    if (DateTime.UtcNow - start).TotalMilliseconds >= float timeoutMs then
                        return raise (TimeoutException(sprintf "Waited too long for the port %d on host %s" port host))
                    else
                        do! Task.Delay(50) |> Async.AwaitTask
                        return! loop start
            with
            | :? SocketException as ex ->
                if (DateTime.UtcNow - start).TotalMilliseconds >= float timeoutMs then
                    return raise (TimeoutException(sprintf "Waited too long for the port %d on host %s" port host))
                else
                    do! Task.Delay(50) |> Async.AwaitTask
                    return! loop start
        }
        loop DateTime.UtcNow

module Core =
    let version () = "0.1.0"
