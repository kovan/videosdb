<template lang="pug">
v-container
  h1.text-center Randin vudei
  Explorer(ordering='-like_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: "Randin vudei",
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