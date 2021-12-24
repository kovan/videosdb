process.on('unhandledRejection', (error) => {
    console.trace(error);
});
var AsyncLock = require('async-lock');
import { getDb, videoToSitemapEntry, FIREBASE_SETTINGS } from "../utils/utils"

var lock = new AsyncLock();
const NodeCache = require("node-cache");

var cache = null


async function getSitemap(dbOptions) {
    await generateCache(dbOptions)

    function transformCategory(cat) {
        return {
            url: `/category/${cat.videosdb.slug}`,
            priority: 0.1
        }
    }

    var sitemap = [
        {
            url: "/",
            changefreq: "daily",
        },
    ]

    cache.keys().forEach((key) => {

        let item = cache.get(key)
        if (key.indexOf("/category/") != -1)
            sitemap.push(transformCategory(item))
        if (key.indexOf("/video/") != -1)
            sitemap.push(videoToSitemapEntry(item))
    })

    return sitemap
}



async function generateCache(dbOptions) {
    await lock.acquire("cache", async function (done) {
        if (cache) {
            done()
            return
        }
        let db = getDb(dbOptions)
        console.debug("initializing cache")
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

        done()
    })
}

async function generateRoutes(dbOptions) {
    await generateCache(dbOptions)


    let routes = []
    cache.keys().forEach((key) => {
        let route = {
            route: key,
            payload: {
                obj: cache.get(key)
            }
        }
        routes.push(route)
    })
    if (process.env.DEBUG)
        routes = [routes[0]]

    return routes
}

export default function (moduleOptions) {
    this.nuxt.hook('generate:before', async (generator, generateOptions) => {

        generateOptions.routes = await generateRoutes(FIREBASE_SETTINGS)
    })


    // this.nuxt.hook('sitemap:generate:before', async (nuxt, sitemapOptions) => {

    //     sitemapOptions.routes = async () => {
    //         return getSitemap(nuxt.options.publicRuntimeConfig.firebase);
    //     }

    // })

}

export { getSitemap }