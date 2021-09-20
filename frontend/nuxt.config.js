

export default {
  modern: true,
  ssr: false,
  target: "static",
  
  // Global page headers (https://go.nuxtjs.dev/config-head)
  head() {
    return {
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { "http-equiv": "content-language", content: "en"}
        ,
      ],
      link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
    }
  },

  generate: {
    routes: [
      "/"
    ],
    fallback: true,
    crawler: false

  },
  // Global CSS (https://go.nuxtjs.dev/config-css)
  // css: ['@/assets/scss/custom.scss'],

  // Plugins to run before rendering page (https://go.nuxtjs.dev/config-plugins)
  plugins: [
    {
      src: '~/plugins/vue-plugin-load-script.js',
      ssr: false,
    },
    {
      src: '~/plugins/bootstrap-vue.js',
    },
    {
      src: '~/plugins/vue-youtube.js',
      ssr: false
    },    
  ],

  // Auto import components (https://go.nuxtjs.dev/config-components)
  components: true,

  // Modules for dev and build (recommended) (https://go.nuxtjs.dev/config-modules)
  buildModules: [
    '@nuxtjs/router-extras',
    '@nuxtjs/google-analytics',
    '@/modules/sitemap-generator'
  ],

  googleAnalytics: {
    id: 'UA-171658328-1',
  },

  // Modules (https://go.nuxtjs.dev/config-modules)
  modules: [
    // https://go.nuxtjs.dev/axios
    '@nuxtjs/axios',
    '@nuxtjs/sitemap'
    // 'bootstrap-vue/nuxt',
  ],

  // bootstrapVue: {
  //   bootstrapCSS: false,
  //   bootstrapVueCSS: false,
  // },

  // Axios module configuration (https://go.nuxtjs.dev/config-axios)
  axios: {
    //proxy: true,
    debug: process.env.DEBUG ? true : false,
    baseURL:  process.env.API_URL || 'http://localhost:8000/api'
  },

  // privateRuntimeConfig: {
  //   axios: {
  //     baseURL: process.env.BASE_URL,
  //   },
  // },

  sitemap: {
    cacheTime: 86400000, // 24h
    hostname: "https://www.sadhguru.digital",
    gzip: true,
    routes: [],
  },

  // proxy: {
  //   '': ApiURL,
  // },

  // Build Configuration (https://go.nuxtjs.dev/config-build)
  build: {
    extend(config, ctx) {
      if (ctx.isDev) {
        config.devtool = 'inline-source-map'
      } else {
        if (ctx.isClient) {
           config.optimization.splitChunks.maxSize = 250000
        }
      }
    },
    loaders:  {
      vue: {
         prettify: false
      }
    },
    optimizeCSS: true,
    parallel: true,
    cache: true,
    //hardSource: false
  },
  server: {
    // https:
    //   process.env.NODE_ENV !== 'production'
    //     ? {
    //         key: fs.readFileSync(path.resolve(__dirname, 'server.key')),
    //         cert: fs.readFileSync(path.resolve(__dirname, 'server.crt')),
    //       }
    //     : {},
  },

  env: {},

  serverMiddleware: [],
}
