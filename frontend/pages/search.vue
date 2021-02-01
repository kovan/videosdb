<template lang="pug">
div
  client-only
    div.gcse-search
</template>

<script>
const gcs_url = "https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635"

export default {
  mounted() {
    this.$loadScript(gcs_url)
  },
  destroyed() {
    this.$unloadScript(gcs_url)
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