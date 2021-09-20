import { getSitemap } from './modules/sitemap-generator'

const os = require('os')
const cpuCount = os.cpus().length
const ApiURL = process.env.API_URL || 'http://localhost:8000/api'

export default {
  modern: true,
  ssr: true,
  target: "static",
  telemetry: false,
  


  generate: {
    workers: cpuCount,
    workerConcurrency: 500,
    routes: [
      "/"
    ],
    fallback: true,
    crawler: false

  },

  css: [],


  plugins: [
    {
      src: '~/plugins/vue-plugin-load-script.js',
      ssr: false,
    },
    // {
    //   src: '~/plugins/bootstrap-vue.js',
    // },
    {
      src: '~/plugins/vue-youtube.js',
      ssr: false
    },    
  ],

  components: true,

  buildModules: [
    '@nuxtjs/router-extras',
    '@nuxtjs/google-analytics',
    '@/modules/sitemap-generator'
    
  ],

  googleAnalytics: {
    id: 'UA-171658328-1',
  },


  modules: [
    // https://go.nuxtjs.dev/axios
    '@nuxtjs/router-extras',
    '@nuxtjs/axios',
    '@nuxtjs/sitemap',
    'bootstrap-vue/nuxt',
  ],

  bootstrapVue: {
    // bootstrapCSS: false,
    // bootstrapVueCSS: false,
    componentPlugins: [
      'LayoutPlugin',
      'FormSelectPlugin',
      'ImagePlugin',
      'PopoverPlugin',
      'PaginationNavPlugin',
      'ButtonPlugin',
      'NavPlugin',
      'CardPlugin',
      'EmbedPlugin',
      'LinkPlugin',
      'SidebarPlugin'
      
    ],
    directivePlugins: [],
    components: ["BIcon", "BIconSearch", "BIconShuffle"],
    directives: []
  },

  axios: {
    //proxy: true,
    debug: process.env.DEBUG ? true : false,
    baseURL:  ApiURL
  },


  sitemap: {
    cacheTime: 86400000, // 24h
    hostname: "https://www.sadhguru.digital",
    gzip: true,
    routes: async () => {
      return getSitemap(ApiURL)
    }
  },


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
  server: {},

  env: {},

  serverMiddleware: [],

  head: {
      title: "Sadhguru wisdom",
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { "http-equiv": "content-language", content: "en"},
        { 
          hid: 'description',
          name: 'description',
          content: 'Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.'          
        }
        ,
      ],
      link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
    
  },  
}
