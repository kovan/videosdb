const firebase = require("firebase");
// Required for side-effects
require("firebase/firestore");

function createDb(config) {


    const firebaseApp = firebase.initializeApp({
        apiKey: config.apiKey,
        authDomain: config.authDomain,
        projectId: config.projectId
    });

    let db = firebase.firestore()
    if (process.env.DEBUG) {
        db.useEmulator("127.0.0.1", 6001);
    }
    return db;
}


var sitemap = null

async function generateSitemap(firestore) {


    function transform(obj, type) {
        if (type == "videos")
            return {
                url: `/video/${obj.slug}`,
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
        else
            return {
                url: `/category/${obj.videosdb.slug}/`,
                priority: 0.1
            }
    }

    var sitemap = [
        {
            url: "/",
            changefreq: "daily",
        },
    ]
    const PAGE_SIZE = 20

    async function download(firestore, type, startAfter = null) {
        //let response = await api.get(url)
        //let container = type == "category" ? response.data : response.data.results
        let query = firestore.collection(type).limit(PAGE_SIZE)
        if (startAfter)
            query = query.startAfter(startAfter)
        let results = await query.get()
        results.forEach((item) => {
            sitemap.push(transform(item.data(), type))
        })
        if (results.docs.length == PAGE_SIZE)
            await download(firestore, type, results.docs.at(-1))
    }

    await Promise.all([
        download(firestore, "videos"),
        download(firestore, "playlists")
    ])

    return sitemap
}



async function getSitemap(firestore) {
    if (sitemap) {
        return sitemap;
    }

    sitemap = generateSitemap(firestore);
    return sitemap;
}



export default function (moduleOptions) {
    this.nuxt.hook('generate:before', async (generator, generateOptions) => {

        generator.$db = createDb(generator.options.publicRuntimeConfig.firebase)

        generateOptions.routes = async () => {
            // if (process.env.DEBUG) {
            //     return [
            //         "/video/sadhguru-about-dismantling-global-hindutva-conference/",
            //     ];
            // }
            try {
                let sitemap = await getSitemap(generator.$db);
                return sitemap.map((route) => route.url);
            } catch (e) {
                console.error(e);
            }
        }
    })

    // this.nuxt.hook('sitemap:generate:before', async (nuxt, sitemapOptions) => {
    //     sitemapOptions.routes = async () => {
    //         return getSitemap(nuxt);
    //     }
    // })

}