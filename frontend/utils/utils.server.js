import axios from "axios";

import { registerInterceptor } from 'axios-cached-dns-resolve'
require("axios-debug-log");
import { cacheAdapterEnhancer } from 'axios-extensions';

function createAxios(baseURL) {
        let myaxios =  axios.create({
            baseURL: baseURL,
            adapter: cacheAdapterEnhancer(axios.defaults.adapter)
        })  
        registerInterceptor(myaxios)

        console.log("Axios created. baseURL: " + baseURL)
        return myaxios
}

var sitemap = null
var api = null

async function generateSitemap(baseURL) {


  function transform(obj, type) {
    if (type == "video") 
      return {
        url: `/video/${obj.slug}/`,
        video: [
          {
            thumbnail_loc: obj.thumbnails.medium.url,
            title: obj.title,
            description: obj.description_trimmed
              ? obj.description_trimmed
              : obj.title,
            content_loc:
              "https://videos.sadhguru.digital/" +
              encodeURIComponent(obj.filename),
            player_loc: `https://www.youtube.com/watch?v=${obj.youtube_id}`,
            duration: obj.duration_seconds,
          },
        ],
        lastmod: obj.modified_date,
        priority: 0.9,
      }      
    else
      return {
        url: `/${type}/${obj.slug}/`,
      }
  }

  var results = [
    {
      url: "/",
      changefreq: "daily",
    },
  ]  
  
  async function download(url, type) {
    try {
      let response = await api.get(url)
      let container = type == "category" ? response.data : response.data.results
      container.forEach((item) => {
        results.push(transform(item, type))
      })
      if (response.data.next)
        await download(response.data.next, type)

    } catch (e) {
      console.error(e)
    }    
  }

  await Promise.all([
    download(baseURL + "/videos/", "video"),
    download(baseURL + "/categories/", "category"),
    download(baseURL + "/tags/", "tag")
  ])

  return results
}


async function getSitemap(baseURL) {
  if (sitemap) {
    return sitemap;
  }

  api = createAxios(baseURL)


  sitemap = generateSitemap(baseURL);
  return sitemap;
}

export { getSitemap, createAxios};
