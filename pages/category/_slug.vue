<template lang="pug">
v-container
    h1.text-center Category: {{this.category.name}}
    Explorer(:categories="this.category.id" ordering='-favorite_count')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  data: () => {
    return {
      category: {}
    }
  },

  async asyncData ({$axios, params}) {
    let url = "/api/categories/" + params.slug
    let response = await $axios.$get(url)
    return { category: response }
  }
}
</script>