<template lang="pug">
b-container
  h2.text-center Category: {{ this.category.name }}
  Explorer(:categories='this.category.id')
</template>

<script>
import handleAxiosError from "~/utils/utils"
export default {
  head () {
    return {
      title: this.category.name,
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
    let url = "/api/categories/" + params.slug
    try {
      let response = await $axios.$get(url)
      return { category: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>
