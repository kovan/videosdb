<template lang="pug">
v-container
  v-card
    v-card-title(align="center") 
      | {{ this.video.title }}
    v-card-text(align="center")
      iframe(
        width='560',
        height='315',
        :src='"https:/www.youtube.com/embed/" + this.video.youtube_id',
        frameborder='0',
        allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
        allowfullscreen
      )
    v-divider
    v-card-text(style="white-space:pre-line;")
      | {{ this.video.description_trimmed }}
    v-divider
    v-card-text
      | {{ this.video.transcription }}
    v-divider
    v-card-title
      | Categories
    v-card-text(v-for='cat in this.video.categories' :key="cat.name")
      | {{ cat }}
    v-divider
    v-card-title
      | Tags
    v-card-text
      v-chip-group(column)
        v-chip(v-for='tag in this.video.tags' :key="tag.name")
          | {{ tag }}
    v-card-actions
      v-btn(color='deep-purple lighten-2')
        | Share


</template>
<script>
import axios from "axios";

export default {
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
  data() {
    return {
      video: {}
    }
  },
  async asyncData ({ $axios, params }) {
    let video = await $axios.$get('/api/videos/' + params.slug + "/")
    return { video }
  }
}
</script>
