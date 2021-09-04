import path from 'path'
import fs from 'fs'

export default {
  // target: 'static',
  // Global page headers (https://go.nuxtjs.dev/config-head)
  head() {
    return {
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        ,
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
    {
      src: '~/plugins/bootstrap-vue.js',
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
    // 'bootstrap-vue/nuxt',
  ],

  // bootstrapVue: {
  //   bootstrapCSS: false,
  //   bootstrapVueCSS: false,
  // },

  // Axios module configuration (https://go.nuxtjs.dev/config-axios)
  axios: {
    proxy: true,
    debug: process.env.DEBUG ? true : false,
    baseURL: process.env.API_URL || 'http://localhost:8000',
  },

  // privateRuntimeConfig: {
  //   axios: {
  //     baseURL: process.env.BASE_URL,
  //   },
  // },

  proxy: {
    '/api': process.env.API_URL || 'http://localhost:8000',
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
