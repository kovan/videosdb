
import axios from 'axios'

const ApiURL = process.env.API_URL || 'http://localhost:8000/api';

export default {
  modern: true,
  ssr: false,
  
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
    fallback: true
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
    '@nuxtjs/google-analytics',
    '@nuxtjs/router',
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
    baseURL: ApiURL
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
    routes: async () => {
      let [ videos, categories, tags ] = await Promise.all([
        axios.get(ApiURL +'/videos/?no_pagination'),
        axios.get(ApiURL +'/categories/?no_pagination'),
        axios.get(ApiURL +'/tags/?no_pagination')
      ])

      videos =  videos.data.map( (video) => {
        return {
          url: `/video/${video.slug}`,
          video: [{
              thumbnail_loc: video.thumbnails.medium.url,
              title: video.title,
              description: video.description_trimmed ? video.description_trimmed : video.title,
              content_loc: "https://videos.sadhguru.digital/" + encodeURIComponent(video.filename),
              player_loc: `https://www.youtube.com/watch?v=${video.youtube_id}`,
              duration: video.duration_seconds
            }
          ],
          lastmod: video.modified_date,
          priority: 0.9
        }
      })
      
      let result =  videos.concat(
        categories.data.map( (cat) => `/category/${cat.slug}`).concat(
          tags.data.map( (tag) => `/tag/${tag.slug}`)))
        
      result.push({
        url: "/",
        changefreq: "daily"
      })

      return result


    },
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
