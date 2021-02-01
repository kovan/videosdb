<template lang="pug">
v-container
  h1.text-center Random video
  Explorer()
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
          content: "Random video"
        }
      ],
    }
  }
}
</script>