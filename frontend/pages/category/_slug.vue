<template lang="pug">
b-container
  h2.text-center Category: {{ this.category.name }}
  Explorer(:categories='this.category.id')
</template>

<script>
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

  async asyncData ({ $axios, params }) {
    let url = "/api/categories/" + params.slug
    try {
      let response = await $axios.$get(url)
      return { category: response }
    } catch (error) {
      console.error(error)
    }
  }
}
</script>
