<template lang="pug">
v-container
  h1.text-center Latest videos
  Explorer(ordering='-yt_published_date')
</template>

<script>
import Explorer from '~/components/Explorer.vue'

export default {
  head () {
    return {
      title: "Latest Sadhguru videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Latest Sadhguru videos"
        }
      ],
    }
  }
}
</script>
