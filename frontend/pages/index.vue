<template lang="pug">
  Explorer()
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

<style>

</style>