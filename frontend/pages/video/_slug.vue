<template lang="pug">
b-container
  b-card
    b-card-title(align='center') 
      | {{ this.video.title }}
    b-card-text(align='center')
    YoutubeEmbedLite(
      :vid="this.video.youtube_id"

    )

    b-card-text
      | {{ this.video.description_trimmed }}

    b-card-text
      | {{ this.video.transcription }}

    b-card(v-if="this.video.categories")
      b-card-title
        | Categories
      b-card-text
        ul
          li(v-for='cat in this.video.categories', :key='cat.id')
            NuxtLink(:to='"/category/" + cat.slug')
              | {{ cat.name }}

    b-card(v-if="this.video.tags")    
      b-card-title(v-if="this.video.tags")
        | Tags
      b-card-text
        b-chip-group(column)
          b-chip(v-for='tag in this.video.tags', :key='tag.id')
            NuxtLink(:to='"/tag/" + tag.slug')
              | {{ tag.name }}
    //- b-card-actions
    //-   b-btn(color='deep-purple lighten-2')
    //-     | Share
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

