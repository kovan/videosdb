import { getSitemap } from "./utils/utils";
import { getStats } from 'axios-cached-dns-resolve'

const os = require("os");
const cpuCount = os.cpus().length;
const baseURL = process.env.API_URL || "http://localhost/api"

export default {
  ssr: true,
  target: "static",
  telemetry: false,

  publicRuntimeConfig: {
    title: "Sadhguru wisdom",
    subtitle: "Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.",
    firebase: {
      apiKey: "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU",
      authDomain: "worpdress-279321.firebaseapp.com",
      projectId: "worpdress-279321",
    }
  },

  generate: {
    concurrency: 100,
    fallback: true,
    crawler: false,
    devtools: true,
    interval: 100, // in milliseconds
    manifest: false,
  },

  //css: ["~/assets/scss/custom.scss"],
  // render: {
  //   resourceHints: false
  // },

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
  },
  ],

  components: true,

  buildModules: [
    "@nuxtjs/google-analytics",
    "@nuxtjs/router-extras",
    "bootstrap-vue/nuxt",
    //'@nuxtjs/firebase',
    "@nuxtjs/sitemap",
    "~/modules/mymodule.js"],

  modules: [],

  firebase: {
    config: {
      apiKey: "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU",
      authDomain: "worpdress-279321.firebaseapp.com",
      projectId: "worpdress-279321",
      storageBucket: "worpdress-279321.appspot.com",
      messagingSenderId: "149555456673",
      appId: "1:149555456673:web:5bb83ccdf79e8e47b3dee0",
      measurementId: "G-CPNNB5CBJM"
    },
    services: {
      firestore: {

        emulatorHost: process.env.NODE_ENV === 'development' ? "127.0.0.1" : undefined,
        emulatorPort: process.env.NODE_ENV === 'development' ? 6001 : undefined
      },
      analytics: true
    },
    onFirebaseHosting: true,
    terminateDatabasesAfterGenerate: true
  },

  bootstrapVue: {
    bootstrapCSS: true,
    bootstrapVueCSS: true,
    componentPlugins: [
      "LayoutPlugin",
      "FormSelectPlugin",
      "ImagePlugin",
      "PopoverPlugin",
      "PaginationNavPlugin",
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
