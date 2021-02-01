<template lang="pug">
  Explorer()
</template>

<script>
import Explorer from '~/components/Explorer.vue'

export default {
  head () {
    return {
      title: "Latest videos",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Latest videos"
        }
      ],
    }
  }
}
</script>

<style>

</style>