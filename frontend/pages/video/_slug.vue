<template lang="pug">
b-container
  b-card(:title="this.video.title")

    b-card-text
      YoutubeEmbedLite(:vid="this.video.youtube_id")

    b-card-text
      | {{ this.video.description_trimmed }}

    b-card-text
      | {{ this.video.transcription }}

    b-card-text(v-if="this.video.categories")
      b-card(title="Categories")
        b-card-text
          ul
            li(v-for='cat in this.video.categories', :key='cat.id')
              NuxtLink(:to='"/category/" + cat.slug')
                | {{ cat.name }}
    b-card-text(v-if="this.video.tags")
      b-card(title="Tags")    
        b-card-text
          NuxtLink(:to='"/tag/" + tag.slug' v-for='tag in this.video.tags', :key='tag.id')
            b-button(size="sm" pill)
              | {{ tag.name }}

</template>
<script>

import YoutubeEmbedLite from "@miyaoka/vue-youtube-embed-lite"


export default {
  components: {
    YoutubeEmbedLite
  },
  head () {
    return {
      title: this.video.title,
      meta: [
        {
          hid: "description",
          name: "description",
          content: this.video.description
        }
      ]
    }
  },
  data () {
    return {
      video: {}
    }
  },
  async asyncData ({ $axios, params }) {
    try {
      let video = await $axios.$get('/api/videos/' + params.slug + "/")
      return { video }      
    } catch (error) {
      console.error(error)
    }       
  }
}
</script>

<style>

</style>

