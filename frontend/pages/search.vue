<template lang="pug">
div
  h6 Search results for term: {{search_query}}
  Explorer(:search='search_query')
</template>

<script>
import Explorer from '~/components/Explorer.vue'

export default {
  head () {
    return {
      title: "Search results",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Search results"
        }
      ],
    }
  },
  computed: {
      search_query() {
           return this.$route.query.q
      }
  }
}
</script>

<style>

</style>