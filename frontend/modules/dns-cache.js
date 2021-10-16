
export default function() {
  this.nuxt.hook('generate:before', async generator => {
    const http = require("http");
    const CacheableLookup = require("cacheable-lookup");
    let cacheable = new CacheableLookup({
      // Set any custom options here
    });
    //cacheable.servers = ["8.8.4.4", "8.8.8.8"];

    // Or configure this as the default for all requests:
    cacheable.install(http.globalAgent);
  })
}