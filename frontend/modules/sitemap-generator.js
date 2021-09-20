import axios from 'axios'
require('axios-debug-log')

async function generate_sitemap(baseURL) {

  let [ videos, categories, tags ] = await Promise.all([
    axios.get(baseURL +'/videos/?no_pagination'),
    axios.get(baseURL +'/categories/?no_pagination'),
    axios.get(baseURL +'/tags/?no_pagination')
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
  function transform(obj, type) {
    return {
      url: `/${type}/${obj.slug}`
    }
  }

  let result =  videos
  
  result = result.concat(
    categories.data.map((cat) => transform(cat, "category")))

  result = result.concat(
    tags.data.map((tag) => transform(tag, "tag")))
    
  result.push({
    url: "/",
    changefreq: "daily"
  })

  return result;
}

export default  function () {
  this.nuxt.hook('generate:extendRoutes', async (routes) => {
    console.debug("adding routes")
    try {
      let baseURL = this.nuxt.options.axios.baseURL
      let sitemap = await generate_sitemap(baseURL)
      this.nuxt.options.sitemap.routes = sitemap
      let newRoutes = sitemap.map( entry => {
        return { 
          route: entry.url, 
          payload: null
        }})
      routes.push(...newRoutes)
    } catch (e) {
      console.error(e)
    }
    
  })
}