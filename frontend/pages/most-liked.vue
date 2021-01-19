<template lang="pug">
v-container
  h1.text-center Most liked videos
  Explorer(ordering='-like_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: "Most liked Sadhguru videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Most liked Sadhguru videos"
        }
      ],
    }
  }
}
</script>