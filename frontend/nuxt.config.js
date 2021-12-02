import { getSitemap } from "./modules/mymodule.js"
import { getVuexData } from "./utils/utils"

const FIREBASE_SETTINGS = {
  apiKey: "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU",
  authDomain: "worpdress-279321.firebaseapp.com",
  projectId: "worpdress-279321",
  storageBucket: "worpdress-279321.appspot.com",
  messagingSenderId: "149555456673",
  appId: "1:149555456673:web:5bb83ccdf79e8e47b3dee0",
  measurementId: "G-CPNNB5CBJM"
}

export default {
  ssr: true,
  target: "static",
  telemetry: false,

  publicRuntimeConfig: {
    title: "Sadhguru wisdom",
    subtitle: "Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.",
    firebase: FIREBASE_SETTINGS
  },

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
    asyncScripts: true,
  },

  plugins: [{
    src: "~/plugins/myplugin.js"
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
    prefetchLinks: false
  },
  components: true,

  buildModules: [
    "@nuxtjs/google-analytics",
    "@nuxtjs/router-extras",
    "bootstrap-vue/nuxt",
    //'@nuxtjs/firebase',
    "@nuxtjs/sitemap",
    "~/modules/mymodule.js"],

  modules: [],

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
    hostname: "https://www.sadhguru.digital",
    gzip: true,
    routes: async () => {
      return await getSitemap(FIREBASE_SETTINGS)
    }
  },

  build: {
    extend(config, ctx) {
      if (ctx.isClient) {
        config.devtool = 'source-map';
        config.optimization.splitChunks.maxSize = 250000;
      }
    },
    loaders: {
      vue: {
        prettify: false,
      },
    },
    optimizeCSS: true,
    extractCSS: true,
    //parallel: true,
    //cache: true,
    //hardSource: false
    babel: {
      presets({ isClient }, preset) {
        if (isClient) {
          // https://babeljs.io/docs/en/babel-preset-env
          preset[1].targets = {
            chrome: "58",
          };
        }
        return [preset];
      },
    },
  },
  server: {},

  env: {},

  serverMiddleware: [],

  hooks: {
    generate: {
      async route({ setPayload }) {
        let vuex_data = await getVuexData(FIREBASE_SETTINGS)
        setPayload({ vuex_data })
      }
    }
  },

  head: {
    htmlAttrs: {
      lang: "en",
    },
    title: "Sadhguru wisdom",
    meta: [
      { charset: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { "http-equiv": "content-language", content: "en" },
      {
        hid: "description",
        name: "description",
        content:
          "Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.",
      },
    ],
    link: [{ rel: "icon", type: "image/x-icon", href: "/favicon.ico" }],
  },

  googleAnalytics: {
    id: "UA-171658328-1",
  },
};
