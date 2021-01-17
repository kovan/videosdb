<template lang="pug">
v-container
  h1.text-center Most commented videos
  Explorer(ordering='-comment_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: "Most commented Sadhguru videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Most commented Sadhguru videos"
        }
      ],
    }
  }
}
</script>