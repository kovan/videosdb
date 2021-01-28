<template lang="pug">
div
  b-card(:title="this.video.title")

    b-card-text
      YoutubeEmbedLite(:vid="this.video.youtube_id" thumb-quality="hq")

    b-card-text(style='white-space: pre-line')
      h6 Description
      p {{ this.video.description_trimmed }}


    b-card-text(v-if="this.video.categories")
      h6 Categories
      ul
        li(v-for='cat in this.video.categories', :key='cat.id')
          NuxtLink(:to='"/category/" + cat.slug')
            | {{ cat.name }}
    b-card-text(v-if="this.video.tags")
      h6 Tags
      NuxtLink.p-1(:to='"/tag/" + tag.slug' v-for='tag in this.video.tags', :key='tag.id') 
        b-button.mt-1(size="sm" pill) 
          | {{ tag.name }}

    b-card-text(v-if="this.video.transcript")
      h6 Transcription:
      small {{ this.video.transcript }}          

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

