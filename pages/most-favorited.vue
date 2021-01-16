<template lang="pug">
v-container
  h1.text-center Most favorited videos
  Explorer(ordering='-favorite_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: "Most favorited Sadhguru videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Most favorited Sadhguru videos"
        }
      ],
    }
  }
}
</script>