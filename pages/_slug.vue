<template lang="pug">
v-container
  | {{this.video.title}}
  iframe(
    width='560',
    height='315',
    :src='"https:/www.youtube.com/embed/" + this.video.youtube_id',
    frameborder='0',
    allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
    allowfullscreen
  )
  | {{this.video.categories}}
  | {{this.video.description}}
  |
  | {{this.video.transcription}}
  |
  | {{this.video.tags}}
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
  async asyncData ({ $axios, params }) {
    let video = await $axios.$get('/api/videos/' + params.slug + "/")
    return { video }
  }
}
</script>
