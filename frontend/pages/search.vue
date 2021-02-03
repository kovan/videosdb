<template lang="pug">
div
  client-only
    .gcse-search
</template>

<script>


export default {
  data () {
    return {
      loaded: false
    }
  },
  mounted () {
    const gcs_url = this.$config.gcs_url
    this.$loadScript(gcs_url).then(() => {
      this.loaded = true
    })
  },
  destroyed () {
    const gcs_url = this.$config.gcs_url
    this.$unloadScript(gcs_url).then(() => {
      this.loaded = false
    })
  },
  head () {
    return {
      title: "Search",
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