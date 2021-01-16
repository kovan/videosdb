<template lang="pug">
v-container
  v-card
    v-card-title(align='center') 
      | {{ this.video.title }}
    v-card-text(align='center')
    youtube(
      ref='youtube',
      :video-id='video.youtube_id',
      :player-vars='{ autoplay: 0, modestbranding: 1, showinfo: 0, rel: 0 }',
      fit-parent
    )
    v-divider
    v-card-text(style='white-space: pre-line')
      | {{ this.video.description_trimmed }}
    v-divider
    v-card-text
      | {{ this.video.transcription }}
    v-divider
    v-card-title
      | Categories
    ul
      li(v-for='cat in this.video.categories', :key='cat.id')
        NuxtLink(:to='"/category/" + cat.slug')
          | {{ cat.name }}
    v-divider
    v-card-title
      | Tags
    v-card-text
      v-chip-group(column)
        v-chip(v-for='tag in this.video.tags', :key='tag.id')
          NuxtLink(:to='"/tag/" + tag.slug')
            | {{ tag.name }}
    //- v-card-actions
    //-   v-btn(color='deep-purple lighten-2')
    //-     | Share
</template>
<script>




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
  data () {
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

<style scoped>
.v-card__text,
.v-card__title {
  word-break: normal; /* maybe !important  */
}
</style>
