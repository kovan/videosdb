<template lang="pug">
b-container.p-0.m-0
  h1.text-center Category: {{ this.category.name }}
  Explorer(
    :current_page='this.$route.params.page || 1',
    :base_url='`/category/${this.$route.params.slug}/`',
    :categories='this.category.id'
  )
</template>

<script>
import { handleAxiosError } from "~/utils/utils"
export default {
  head () {
    return {
      title: this.category.name + " - " + "Sadhguru wisdom",
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
    let url = "/categories/" + params.slug + "/"
    try {
      let response = await $axios.$get(url)
      return { category: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>

<router>
  {
    path: '/category/:slug'
  }
</router>