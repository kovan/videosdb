namespace VideosDb.Tests

open System
open Xunit
open VideosDb
open System.Threading.Tasks

module UtilsTests =

    [<Fact>]
    let ``putItemAtFront rotates sequence`` () =
        let seq = ["a"; "b"; "c"] |> Seq.ofList
        let res = Utils.putItemAtFront seq "b" |> Seq.toList
        Assert.Equal(["b"; "c"; "a"], res)

    [<Fact>]
    let ``waitForPortAsync times out for closed port`` () =
        let task = Utils.waitForPortAsync "127.0.0.1" 54321 100
        Assert.ThrowsAsync<TimeoutException>(fun () -> task) |> Async.AwaitTask |> Async.RunSynchronously

    [<Fact>]
    let ``settings default port`` () =
        Assert.Equal(5001, Settings.IPFS_PORT)
