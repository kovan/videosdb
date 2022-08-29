<template lang="pug">
div
  h2.text-center Search
  client-only
    .gcse-search
</template>

<script>
const URL = 'https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635'
export default {
  data() {
    return {
      loaded: false,
    }
  },
  mounted() {
    this.$loadScript(URL).then(() => {
      this.loaded = true
    })
  },
  destroyed() {
    this.$unloadScript(URL).then(() => {
      this.loaded = false
    })
  },
  head() {
    return {
      title: 'Search' + ' - ' + this.$config.title,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: 'Search',
        },
      ]
    }
  },
  async asyncData({ payload, store }) {
    if (payload) {
      store.commit('setInitial', payload.vuex_data)
    }
  },
}
</script>

<style>
</style>

<router>
  {
    path: '/search'
  }
</router>
