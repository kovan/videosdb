<template lang="pug">
b-container.p-0.m-0
  h1.text-center Category: {{ this.category.snippet.title }}
  Explorer(
    :base_url='`/category/${this.$route.params.slug}`',
    :category='this.category'
  )
</template>

<script>
import { getWithCache } from '~/utils/utils'
export default {
  head() {
    return {
      title: this.category.snippet.title + ' - ' + 'Sadhguru wisdom',
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: 'Category: ' + this.category.snippet.title,
        },
      ],
    }
  },
  data: () => {
    return {
      category: {},
    }
  },

  async asyncData({ $db, params, payload, error }) {
    if (payload) return { category: payload }

    const q_category = await getWithCache(
      $db.collection('playlists').where('videosdb.slug', '==', params.slug)
    )

    let category = q_category.docs[0].data()
    return { category }
  },
}
</script>

<router>
  {
    path: '/category/:slug'
  }
</router>