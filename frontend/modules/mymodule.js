installUnhandledExceptionHandlers()

var AsyncLock = require('async-lock');
import { getDb, videoToSitemapEntry, getFirebaseSettings, installUnhandledExceptionHandlers } from "../utils/utils"
import {
    getDoc,
    getDocs,
    limit,
    orderBy,
    where,
    startAfter,
    doc,
    query, collection
} from 'firebase/firestore/lite'


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

        async function download(db, type, startAfterParam = null) {
            let q = query(collection(db, type), limit(PAGE_SIZE))
            q = query(q, where("id", "!=", null))
            if (startAfterParam)
                q = query(q, startAfter(startAfterParam))
            let q_results = await getDocs(q)

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
    // if (process.env.DEBUG)
    //     routes = [routes[0]]

    return routes
}

export default function (moduleOptions) {
    this.nuxt.hook('generate:before', async (generator, generateOptions) => {
        installUnhandledExceptionHandlers()
        generateOptions.routes = await generateRoutes(await getFirebaseSettings())
    })


    // this.nuxt.hook('sitemap:generate:before', async (nuxt, sitemapOptions) => {

    //     sitemapOptions.routes = async () => {
    //         return getSitemap(nuxt.options.publicRuntimeConfig.firebase);
    //     }

    // })

}

export { getSitemap }
