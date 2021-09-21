<template lang="pug">
b-container
  h1.text-center Tag: {{ this.tag.name }}
  Explorer(
    :current_page='this.$route.params.page || 1',
    :base_url='`/tag/${this.$route.params.slug}/`',
    :tags='this.tag.id'
  )
</template>

<script>
import { handleAxiosError } from "~/utils/utils"
export default {
  head () {
    return {
      title: this.tag.name + "Sadhguru wisdom",
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
    let url = "/tags/" + params.slug + "/"
    try {
      let response = await $axios.$get(url)
      return { tag: response }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>

<router>
  {
    path: '/tag/:slug'
  }
</router>