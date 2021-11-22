import { createDb, getWithCache } from "../utils/utils"

const NodeCache = require("node-cache");

var cache = null
var db = null

async function getSitemap(dbOptions) {
    if (!cache)
        await generateCache(dbOptions)

    function transformCategory(obj) {
        return {
            url: `/category/${obj.videosdb.slug}/`,
            priority: 0.1
        }
    }
    function transformVideo(obj) {

        return {
            url: `/video/${obj.videosdb.slug}`,
            video: [
                {
                    thumbnail_loc: obj.snippet.thumbnails.medium.url,
                    title: obj.snippet.title,
                    description: obj.videosdb.descriptionTrimmed
                        ? obj.videosdb.descriptionTrimmed
                        : obj.snippet.title,
                    content_loc:
                        "https://videos.sadhguru.digital/" +
                        encodeURIComponent(obj.videosdb.filename),
                    player_loc: `https://www.sadhguru.digital/video/${obj.videosdb.slug}`,
                    duration: obj.videosdb.duration_seconds,
                },
            ],
            priority: 1.0,
        }


    }

    var sitemap = [
        {
            url: "/",
            changefreq: "daily",
        },
    ]

    cache.keys().forEach((key) => {
        item = cache.get(key)
        if (key.indexOf("/category/" != -1))
            sitemap.push(transformCategory(item))
        if (key.indexOf("/video/" != -1))
            sitemap.push(transformVideo(item))
    })

    return sitemap
}

async function generateCache(dbOptions) {
    if (!db)
        db = createDb(dbOptions)

    cache = new NodeCache({ stdTTL: 0, checkperiod: 0 });

    const PAGE_SIZE = 20
    let typeMap = {
        videos: "video",
        playlists: "category"

    }

    async function download(db, type, startAfter = null) {
        let query = db.collection(type).limit(PAGE_SIZE)
        if (startAfter)
            query = query.startAfter(startAfter)
        let q_results = await query.get()
        q_results.forEach((item) => {
            cache.set(`/${typeMap[type]}/${item.data().videosdb.slug}`, item.data())
        })
        if (q_results.docs.length == PAGE_SIZE)
            await download(db, type, q_results.docs.at(-1))
    }

    await Promise.all([
        download(db, "videos"),
        download(db, "playlists")
    ])
}

async function generateRoutes(dbOptions) {
    if (!cache)
        await generateCache(dbOptions)
    if (!db)
        db = await createDb(dbOptions)

    let routes = []
    cache.keys().forEach((key) => {
        let route = {
            route: key,
            payload: cache.get(key)
        }
        routes.push(route)
    })
    return routes
}

export default function (moduleOptions) {
    this.nuxt.hook('generate:before', async (generator, generateOptions) => {
        //generator.$db = createDb(generator.options.publicRuntimeConfig.firebase)
        generateOptions.routes = await generateRoutes(generator.options.publicRuntimeConfig.firebase)
    })


    this.nuxt.hook('sitemap:generate:before', async (nuxt, sitemapOptions) => {
        sitemapOptions.routes = async () => {
            return getSitemap(nuxt.options.firebase);
        }
    })

}