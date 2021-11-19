import axios from "axios";

import { registerInterceptor } from 'axios-cached-dns-resolve'
require("axios-debug-log");
import { cacheAdapterEnhancer } from 'axios-extensions';

function createAxios(baseURL) {
  let myaxios = axios.create({
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
        url: `/video/${obj.slug}`,
        video: [
          {
            thumbnail_loc: obj.snippet.thumbnails.medium.url,
            title: obj.snippet.title,
            description: obj.videosdb.descriptionTrimmed
              ? obj.videosdb.descriptionTrimmed
              : obj.snippet.title,
            content_loc:
              "https://videos.sadhguru.digital/" +
              encodeURIComponent(obj.videosdb.filename),
            player_loc: `https://www.sadhguru.digital/video/${obj.videosdb.slug}`,
            duration: obj.videosdb.duration_seconds,
          },
        ],
        priority: 1.0,
      }
    else
      return {
        url: `/${type}/${obj.videosdb.slug}/`,
        priority: 0.1
      }
  }

  var results = [
    {
      url: "/",
      changefreq: "daily",
    },
  ]

  async function download(url, type) {
    let response = await api.get(url)
    let container = type == "category" ? response.data : response.data.results
    container.forEach((item) => {
      results.push(transform(item, type))
    })
    if (response.data.next)
      await download(response.data.next, type)
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

export { getSitemap, createAxios };
