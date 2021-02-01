<template lang="pug">
div
  client-only
    div.gcse-search
</template>

<script>
const gcs_url = "https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635"

export default {
  data() {
    return {
      loaded: false
    }
  },
  mounted() {
    this.$loadScript(gcs_url).then(() => {
      this.loaded = true
    })
  },
  destroyed() {
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