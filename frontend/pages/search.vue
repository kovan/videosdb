<template lang="pug">
div
  h2.text-center Search
  client-only
    .gcse-search
</template>

<script>


const URL = 'https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635'
export default {
  data () {
    return {
      loaded: false,
    }
  },
  mounted () {
    this.$loadScript(URL).then(() => {
      this.loaded = true
    })
  },
  destroyed () {
    this.$unloadScript(URL).then(() => {
      this.loaded = false
    })
  },
  head: {

    title: "Search" + " - " + "Sadhguru wisdom",
    meta: [
      {
        hid: 'description',
        name: 'description',
        content: "Search"
      }
    ]

  }
}
</script>

<style>
</style>
