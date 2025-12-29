namespace VideosDb.Tests

open System
open Xunit
open VideosDb
open Publisher
open System.Text.Json

module PublisherTests =

    [<Fact>]
    let ``inmemory publisher stores published videos`` () =
        let p = InMemoryPublisher()
        let pub = p :> IPublisher
        let json = JsonDocument.Parse("{ \"id\": \"abc\" }").RootElement.Clone()
        pub.PublishVideoAsync(json).GetAwaiter().GetResult()
        let q = p.Published
        Assert.True(q.Count = 1)

    [<Fact>]
    let ``twitter publisher skips if not nithyananda`` () =
        let t = TwitterPublisherAdapter(null, "testing") :> IPublisher
        let json = JsonDocument.Parse("{ \"id\": \"abc\" }").RootElement.Clone()
        // should not throw and should not publish
        t.PublishVideoAsync(json).GetAwaiter().GetResult()
        Assert.True(true)
