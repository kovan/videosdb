export default {
  // target: 'static',
  // Global page headers (https://go.nuxtjs.dev/config-head)
  head() {
    return {
      titleTemplate: '%s - ' + this.$config.title,
      title: this.$config.title,
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          hid: 'description',
          name: 'description',
          content: this.$config.subtitle,
        },
      ],
      link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
    }
  },

  // Global CSS (https://go.nuxtjs.dev/config-css)
  // css: ['@/assets/scss/custom.scss'],

  // Plugins to run before rendering page (https://go.nuxtjs.dev/config-plugins)
  plugins: [
    {
      src: '~/plugins/vue-plugin-load-script.js',
      ssr: false,
    },
  ],

  // Auto import components (https://go.nuxtjs.dev/config-components)
  components: true,

  // Modules for dev and build (recommended) (https://go.nuxtjs.dev/config-modules)
  buildModules: ['@nuxtjs/google-analytics'],

  googleAnalytics: {
    id: 'UA-171658328-1',
  },

  // Modules (https://go.nuxtjs.dev/config-modules)
  modules: [
    // https://go.nuxtjs.dev/axios
    '@nuxtjs/axios',
    'bootstrap-vue/nuxt',
  ],

  // bootstrapVue: {
  //   bootstrapCSS: false,
  //   bootstrapVueCSS: false,
  // },

  // Axios module configuration (https://go.nuxtjs.dev/config-axios)
  axios: {
    proxy: true,
    debug: process.env.DEBUG ? true : false,
    baseURL: process.env.API_URL,
  },

  publicRuntimeConfig: {
    title: process.env.VIDEOSDB_TITLE,
    subtitle: process.env.VIDEOSDB_SUBTITLE,
    gcs_url: process.env.GCS_URL,
  },

  // privateRuntimeConfig: {
  //   axios: {
  //     baseURL: process.env.BASE_URL,
  //   },
  // },

  proxy: {
    '/api': process.env.API_URL,
  },

  // Build Configuration (https://go.nuxtjs.dev/config-build)
  build: {
    extend(config, ctx) {
      if (ctx.isDev) {
        config.devtool = 'inline-source-map'
      }
    },
    extractCSS: true,
  },
  // server: {
  //   port: 3000, // default: 3000
  //   host: '0.0.0.0', // default: localhost,
  //   timing: false,
  // },

  env: {},

  serverMiddleware: [],
}
