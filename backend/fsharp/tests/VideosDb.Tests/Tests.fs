namespace VideosDb.Tests

open Xunit
open VideosDb

module Tests =

    [<Fact>]
    let ``Settings default IPFS host`` () =
        Assert.Equal("127.0.0.1", Settings.IPFS_HOST)
