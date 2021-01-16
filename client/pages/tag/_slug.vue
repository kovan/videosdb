<template lang="pug">
v-container
  h1.text-center Tag: {{ this.tag.name }}
  Explorer(:tags='this.tag.id')
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  head () {
    return {
      title: this.tag.name,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Tag: " + this.tag.name
        }
      ],
    }
  },
  data: () => {
    return {
      tag: {}
    }
  },

  async asyncData ({ $axios, params }) {
    let url = "/api/tags/" + params.slug
    let response = await $axios.$get(url)
    return { tag: response }
  }
}
</script>