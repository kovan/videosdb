<template lang="pug">
div
  h2.text-center Search
  client-only
    .gcse-search
</template>

<script>


import { handleAxiosError, getConfigForRequest } from "~/utils/utils"

export default {
  data () {
    return {
      loaded: false
    }
  },
  mounted () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    this.$loadScript(config.gcs_url).then(() => {
      this.loaded = true
    })
  },
  destroyed () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    this.$unloadScript(config.gcs_url).then(() => {
      this.loaded = false
    })
  },
  head () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      title: "Search" + " - " + config.title,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Search"
        }
      ]
    }
  }
}
</script>

<style>
</style>
