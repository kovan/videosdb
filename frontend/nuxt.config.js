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

export default {
    ssr: true,
    target: "static",
    telemetry: false,


    publicRuntimeConfig: { ...myConfig },


    generate: {
        concurrency: 2,
        fallback: true,
        crawler: false,
        devtools: true,
        interval: 0, // in milliseconds
        manifest: false,
        exclude: [/^\/tag/]
    },

    //css: ["~/assets/scss/custom.scss"],
    render: {
        resourceHints: false,
        //asyncScripts: true,
    },

    plugins: [
        {
            src: "~/plugins/myplugin.js"
        },
        {
            src: "~/plugins/unhandled-exceptions.server.js"
        },
        {
            src: "~/plugins/vue-infinite-scroll.js",
            mode: "client"
        }, {
            src: "~/plugins/vue-plugin-load-script.js",
            mode: "client",
        }, {
            src: "~/plugins/vue-youtube.js",
            mode: "client",
        }, {
            src: "~/plugins/vue-keep-scroll.js",
            mode: "client",
        }
    ],

    router: {
        prefetchLinks: false,
        prefetchPayloads: false,
    },
    components: true,

    buildModules: [
        'nuxt-delay-hydration',
        "@nuxtjs/google-analytics",
        "@nuxtjs/router-extras",
        "bootstrap-vue/nuxt",
        //'@nuxtjs/firebase',
        "@nuxtjs/sitemap"
    ],

    modules: [
        'nuxt-ssr-cache',
        "~/modules/mymodule.js"
    ],
    delayHydration: {
        mode: 'mount'
    },
    bootstrapVue: {
        bootstrapCSS: true,
        bootstrapVueCSS: true,
        componentPlugins: [
            "LayoutPlugin",
            "BadgePlugin",
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

    build: {
        extend(config, ctx) {
            const isProd = process.env.NODE_ENV === 'production';
            if (isProd && ctx.isClient) {
                config.optimization.splitChunks.maxSize = 400856;
            }
            if (ctx.isDev) {
                config.devtool = ctx.isClient ? "source-map" : "inline-source-map";
            }
        },
        babel: {
            compact: true,
            presets(env, [preset, options]) {
                return [
                    ["@nuxt/babel-preset-app", {
                        corejs: { version: 3 },
                        targets: {
                            chrome: "58",
                        }
                    }]
                ]
            }
        },


        optimizeCSS: true,
        extractCSS: true,
        //parallel: true,
        //cache: true,
        //hardSource: false

        analyze: false,
        hardSource: false,
        splitChunks: {
            layouts: false,
            pages: false,
            components: false,
        },
        html: {
            minify: {
                minifyCSS: true,
                minifyJS: true
            }
        },
        loaders: {
            vue: {
                prettify: false
            }
        }

    },

    vue: {
        config: {
            productionTip: false,
            devtools: process.env.NODE_ENV == "development"
        }
    },
    server: {},

    env: {},

    serverMiddleware: [],

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
        id: process.env.GOOGLE_ANALYTICS_ID,
    },

    cache: {
        // if you're serving multiple host names (with differing
        // results) from the same server, set this option to true.
        // (cache keys will be prefixed by your host name)
        // if your server is behind a reverse-proxy, please use
        // express or whatever else that uses 'X-Forwarded-Host'
        // header field to provide req.hostname (actual host name)
        useHostPrefix: true,
        pages: [
            // these are prefixes of pages that need to be cached
            // if you want to cache all pages, just include '/'
            '/',
        ],
        store: {
            type: 'memory',

            // maximum number of pages to store in memory
            // if limit is reached, least recently used page
            // is removed.
            max: 100,

            // number of seconds to store this page in cache
            ttl: 3600 * 4,
        },
        // store: {
        //     type: 'redis',
        //     host: 'localhost',
        //     ttl: 10 * 60 * 3600,
        //     configure: [
        //         // these values are configured
        //         // on redis upon initialization
        //         ['maxmemory', '300mb'],
        //         ['maxmemory-policy', 'allkeys-lru'],
        //     ],
        // },
    },
};
