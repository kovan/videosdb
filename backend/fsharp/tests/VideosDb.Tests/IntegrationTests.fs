namespace VideosDb.Tests

open System
open Xunit
open System.Threading.Tasks
open VideosDb
open Publisher
open Db

module IntegrationTests =

    [<Fact(Skip = "Requires external services configured via env vars")>]
    let ``firestore integration smoke test`` () =
        // Only run if env var RUN_INTEGRATION set
        if Environment.GetEnvironmentVariable("RUN_INTEGRATION") <> "true" then
            Assert.True(true)
        else
            let project = match Environment.GetEnvironmentVariable("FIRESTORE_PROJECT") with | null | "" -> "demo-project" | v -> v
            let db = FirestoreAdapter(project) :> IDatabase
            db.InitAsync().GetAwaiter().GetResult()
            Assert.True(true)

    [<Fact(Skip = "Requires external services configured via env vars")>]
    let ``ipfs integration smoke test`` () =
        if Environment.GetEnvironmentVariable("RUN_INTEGRATION") <> "true" then
            Assert.True(true)
        else
            let host = match Environment.GetEnvironmentVariable("IPFS_HOST") with | null | "" -> "127.0.0.1" | v -> v
            let portStr = match Environment.GetEnvironmentVariable("IPFS_PORT") with | null | "" -> "5001" | v -> v
            let port = match Int32.TryParse(portStr) with | true, v -> v | _ -> 5001
            let ipfs = Ipfs.IpfsAdapter(host, port) :> Ipfs.IIpfs
            let hash = ipfs.AddFileAsync("./dummy.txt", true).GetAwaiter().GetResult()
            Assert.False(String.IsNullOrEmpty(hash))
