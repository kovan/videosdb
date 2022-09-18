import { defineNuxtConfig } from '@nuxt/bridge'
import { getSitemap } from "./modules/mymodule.js"
import { getVuexData, getDb, getFirebaseSettings } from "./utils/utils"

let myConfig = {

    title: process.env.VIDEOSDB_TITLE,
    subtitle: process.env.VIDEOSDB_SUBTITLE,
    hostname: process.env.VIDEOSDB_HOSTNAME,
    website: process.env.VIDEOSDB_WEBSITE,
    config: process.env.VIDEOSDB_CONFIG,
    cseUrl: process.env.VIDEOSDB_CSE_URL,
    showTranscripts: process.env.VIDEOSDB_SHOW_TRANSCRIPTS
}


export default defineNuxtConfig({
    ssr: true,
    target: "static",
    telemetry: false,


    publicRuntimeConfig: { ...myConfig },


    generate: {
        concurrency: 200,
        fallback: true,
        crawler: false,
        devtools: true,
        interval: 100, // in milliseconds
        manifest: false,
        exclude: [/^\/tag/]
    },

    //css: ["~/assets/scss/custom.scss"],
    render: {
        resourceHints: false,
        //asyncScripts: true,
    },

    router: {
        prefetchLinks: false,
        prefetchPayloads: false,
    },
    components: true,

    buildModules: [
        // "@nuxtjs/router-extras",
        "bootstrap-vue/nuxt",
        //'@nuxtjs/firebase',
        "@nuxtjs/sitemap",
        // "~/modules/mymodule.js",
        'nuxt-vite'],


    bootstrapVue: {
        bootstrapCSS: true,
        bootstrapVueCSS: true,
        componentPlugins: [
            "LayoutPlugin",
            "FormSelectPlugin",
            "FormInputPlugin",
            "ImagePlugin",
            "PopoverPlugin",
            "ButtonPlugin",
            "NavPlugin",
            "CardPlugin",
            "EmbedPlugin",
            "LinkPlugin",
            "SidebarPlugin",
        ],
        directivePlugins: [],
        components: ["BIcon", "BIconSearch", "BIconShuffle"],
        directives: [],
    },

    sitemap: {
        cacheTime: 86400000 * 2, // 48h
        hostname: myConfig.hostname,
        gzip: true,
        routes: async () => {
            return await getSitemap(await getFirebaseSettings())
        }
    },



    vue: {
        config: {
            productionTip: false,
            devtools: process.env.NODE_ENV == "development"
        }
    },

    hooks: {
        generate: {
            async route({ setPayload }) {
                let db = getDb(await getFirebaseSettings())
                let vuex_data = await getVuexData(db)
                setPayload({ vuex_data })
            }
        }
    },

    head: {
        htmlAttrs: {
            lang: "en",
        },
        title: process.env.VIDEOSDB_TITLE,
        meta: [
            { charset: "utf-8" },
            { name: "viewport", content: "width=device-width, initial-scale=1" },
            { "http-equiv": "content-language", content: "en" },
            {
                hid: "description",
                name: "description",
                content:
                    process.env.VIDEOSDB_SUBTITLE,
            },
        ],
        link: [{ rel: "icon", type: "image/x-icon", href: "/favicon.ico" }],
    },

    googleAnalytics: {
        id: "UA-171658328-1",
    },
    vite: {

    },

    bridge: {
        meta: true,
        nitro: true,
        capi: false,
    },
})
