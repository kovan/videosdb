<template lang="pug">
b-container
  h1.text-center Tag: {{ this.tag.name }}
  Explorer(
    :current_page='this.$route.params.page',
    :base_url='`/tag/${this.$route.params.slug}/`',
    :tags='this.tag.id'
  )
</template>

<script>
import { handleAxiosError, getConfigForRequest } from "~/utils/utils"
export default {
  head () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      title: this.tag.name + " - " + config.title,
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
    let url = "/tags/" + params.slug
    try {
      let response = await $axios.$get(url)
      return { tag: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>
