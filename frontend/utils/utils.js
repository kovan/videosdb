import axios from "axios";
require("axios-debug-log");
var sitemap = null;

function handleAxiosError(axiosError, errorFunc) {
  console.error(axiosError);
  if (axiosError.response) {
    errorFunc({
      statusCode: axiosError.response.status,
      message: axiosError.response.statusText,
    });
  } else {
    errorFunc({
      statusCode: null,
      message: axiosError.code,
    });
  }
}
function getConfigForRequest(req) {
  const host = req
    ? req.headers.host.split(":")[0]
    : typeof window != "undefined"
    ? window.location.host.split(":")[0]
    : null;

  var config = null;

  switch (host) {
    case "nithyananda.yoga":
      config = {
        domain: "nithyananda.yoga",
        title: "KAILASA's Nithyananda",
        subtitle: "",
        gcs_url: "https://cse.google.com/cse.js?cx=043c6e15fcd358d5a",
      };
      break;
    default:
    case "www.sadhguru.digital":
    case "sadhguru.digital":
      config = {
        domain: "sadhguru.digital",
        title: "Sadhguru wisdom",
        subtitle:
          "Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.",
        gcs_url: "https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635",
      };
      break;
  }

  return config;
}

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
      let response = await axios.get(url)
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
  sitemap = generateSitemap(baseURL);
  return sitemap;
}

export { handleAxiosError, getConfigForRequest, getSitemap };
