<template lang="pug">
v-container
    h1.text-center Tag: {{this.tag.name}}
    Explorer(:categories="this.tag.id")
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  data: () => {
    return {
      tag: {}
    }
  },

  async asyncData ({$axios, params}) {
    let url = "/api/tag/" + params.slug
    let response = await $axios.$get(url)
    return { tag: response }
  }
}
</script>