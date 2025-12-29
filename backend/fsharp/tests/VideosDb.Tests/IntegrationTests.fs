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
            let db = FirestoreAdapter(Environment.GetEnvironmentVariable("FIRESTORE_PROJECT") ?? "demo-project") :> IDatabase
            db.InitAsync().GetAwaiter().GetResult()
            Assert.True(true)

    [<Fact(Skip = "Requires external services configured via env vars")>]
    let ``ipfs integration smoke test`` () =
        if Environment.GetEnvironmentVariable("RUN_INTEGRATION") <> "true" then
            Assert.True(true)
        else
            let host = Environment.GetEnvironmentVariable("IPFS_HOST") ?? "127.0.0.1"
            let port = match Int32.TryParse(Environment.GetEnvironmentVariable("IPFS_PORT") ?? "5001") with | true, v -> v | _ -> 5001
            let ipfs = Ipfs.IpfsAdapter(host, port) :> Ipfs.IIpfs
            let hash = ipfs.AddFileAsync("./dummy.txt", true).GetAwaiter().GetResult()
            Assert.False(String.IsNullOrEmpty(hash))
