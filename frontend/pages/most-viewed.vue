<template lang="pug">
v-container
  h1.text-center Most viewed videos
  Explorer(ordering='-view_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: "Most viewed Sadhguru videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Most viewed Sadhguru videos"
        }
      ],
    }
  }
}
</script>