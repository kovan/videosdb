import { getSitemap } from "./utils/utils";

const os = require("os");
const cpuCount = os.cpus().length;
const ApiURL = process.env.API_URL || "http://localhost:8000/api";

export default {
  ssr: true,
  target: "static",
  telemetry: false,

  generate: {
    routes: async () => {
      if (process.env.DEBUG) {
        return [
          "/video/sadhguru-about-dismantling-global-hindutva-conference/",
        ];
      }
      try {
        let sitemap = await getSitemap(ApiURL);
        return sitemap.map((route) => route.url);
      } catch (e) {
        console.error(e);
      }
    },
    concurrency: 100,
    fallback: true,
    crawler: false,
    devtools: true,
    interval: 50, // in milliseconds
    manifest: false,
  },

  //css: ["~/assets/scss/custom.scss"],

  plugins: [
    {
      src: "~/plugins/vue-plugin-load-script.js",
      mode: "client",
    },
    {
      src: "~/plugins/vue-youtube.js",
      mode: "client",
    },
  ],

  components: true,

  buildModules: [
    'nuxt-purgecss',
    "@nuxtjs/google-analytics",
    "@nuxtjs/router-extras",
    "@nuxtjs/axios",
    "@nuxtjs/sitemap",
    "bootstrap-vue/nuxt",
    "~/modules/dns-cache.js"],

  modules: [
  ],
  
  axios: {
    baseURL: ApiURL,
  },

  publicRuntimeConfig: {
    version: process.env.NUXT_ENV_CURRENT_GIT_SHA ,
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
    routes: async () => {
      return getSitemap(ApiURL);
    },
  },

  build: {
    extend(config, ctx) {
      if (ctx.isDev) {
        config.devtool = "inline-source-map";
      } else {
        if (ctx.isClient) {
          config.optimization.splitChunks.maxSize = 250000;
        }
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
