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
  let [videos, categories, tags] = await Promise.all([
    axios.get(baseURL + "/videos/?no_pagination"),
    axios.get(baseURL + "/categories/?no_pagination"),
    axios.get(baseURL + "/tags/?no_pagination"),
  ]);

  videos = videos.data.map((video) => {
    return {
      url: `/video/${video.slug}`,
      video: [
        {
          thumbnail_loc: video.thumbnails.medium.url,
          title: video.title,
          description: video.description_trimmed
            ? video.description_trimmed
            : video.title,
          content_loc:
            "https://videos.sadhguru.digital/" +
            encodeURIComponent(video.filename),
          player_loc: `https://www.youtube.com/watch?v=${video.youtube_id}`,
          duration: video.duration_seconds,
        },
      ],
      lastmod: video.modified_date,
      priority: 0.9,
    };
  });
  function transform(obj, type) {
    return {
      url: `/${type}/${obj.slug}`,
    };
  }

  let result = videos;

  result = result.concat(
    categories.data.map((cat) => transform(cat, "category"))
  );

  result = result.concat(tags.data.map((tag) => transform(tag, "tag")));

  result.push({
    url: "/",
    changefreq: "daily",
  });

  return result;
}
async function getSitemap(baseURL) {
  if (sitemap) {
    return sitemap;
  }
  sitemap = generateSitemap(baseURL);
  return sitemap;
}

export { handleAxiosError, getConfigForRequest, getSitemap };
