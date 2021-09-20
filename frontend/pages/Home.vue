<template lang="pug">
b-container
  Explorer(:current_page='this.$route.params.page || 1', base_url='/')
</template>

<script>
import { getConfigForRequest } from "~/utils/utils"

export default {
  head () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      title: config.title,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: config.subtitle
        }
      ],
    }
  }
}
</script>


<router>
  {
    path: '/:page?'
  }
</router>