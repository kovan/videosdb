<template lang="pug">
b-container
  h2.text-center Tag: {{ this.tag.name }}
  Explorer(:tags='this.tag.id')
</template>

<script>
import handleAxiosError from "~/utils/utils"
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

  async asyncData ({ $axios, params, error }) {
    let url = "/api/tags/" + params.slug
    try {
      let response = await $axios.$get(url)
      return { tag: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>
