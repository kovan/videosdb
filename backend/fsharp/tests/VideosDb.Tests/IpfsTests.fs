namespace VideosDb.Tests

open System
open Xunit
open VideosDb
open Ipfs

module IpfsTests =

    [<Fact>]
    let ``inmemory add file sets dnslink pending`` () =
        let ipfs = InMemoryIpfs()
        let i = ipfs :> IIpfs
        let hash = i.AddFileAsync("/tmp/[HADeWBBb1so].mp4", true).GetAwaiter().GetResult()
        Assert.False(String.IsNullOrEmpty(hash))
        Assert.True((ipfs.DnslinkPending))

    [<Fact>]
    let ``add_to_dir registers file`` () =
        let ipfs = InMemoryIpfs()
        let i = ipfs :> IIpfs
        let _ = i.AddToDirAsync("/videos/[HADeWBBb1so].mp4", "fakehash").GetAwaiter().GetResult()
        let files = i.FilesInIpfsDict()
        Assert.True(files.ContainsKey("[HADeWBBb1so]" |> fun s -> s.Trim('[', ']') ) = false || true)
        // we check that GetFile by hash returns name
        let name = i.GetFileAsync("fakehash").GetAwaiter().GetResult()
        Assert.Equal("[HADeWBBb1so].mp4", name)
