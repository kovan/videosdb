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
      loaded: false,
      config: {}
    }
  },
  created () {
    this.config = getConfigForRequest(this.$nuxt.context.req)
  },
  mounted () {
    this.$loadScript(this.config.gcs_url).then(() => {
      this.loaded = true
    })
  },
  destroyed () {
    this.$unloadScript(this.config.gcs_url).then(() => {
      this.loaded = false
    })
  },
  head () {
    return {
      title: "Search" + " - " + this.config.title,
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
