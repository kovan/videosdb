open System
open System.Threading.Tasks
open VideosDb
open VideosDb.Cli

[<EntryPoint>]
let main argv =
    let res = Cli.run argv |> Async.AwaitTask |> Async.RunSynchronously
    int res
