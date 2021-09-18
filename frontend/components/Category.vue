<template lang="pug">
b-container
  h1.text-center Category: {{ this.category.name }}
  Explorer(
    :current_page='this.$route.params.page || 1',
    :base_url='`/category/${this.$route.params.slug}/`',
    :categories='this.category.id'
  )
</template>

<script>
import { handleAxiosError, getConfigForRequest } from "~/utils/utils"
export default {
  head () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      title: this.category.name + " - " + config.title,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Category: " + this.category.name
        }
      ],
    }
  },
  data: () => {
    return {
      category: {}
    }
  },

  async asyncData ({ $axios, params, error }) {
    let url = "/categories/" + params.slug
    try {
      let response = await $axios.$get(url)
      return { category: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>
