<template lang="pug">
b-container.p-0.m-0
  h1.text-center Category: {{ this.category.snippet.title }}
  Explorer(
    :initial_page='this.$route.params.page || 1',
    :base_url='`/category/${this.$route.params.slug}`',
    :category='this.category'
  )
</template>

<script>
import { collection, getDocs } from 'firebase/firestore/lite'

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

    const q_category = await getDocs(
      collection($db, 'playlists').where('videosdb.slug', '==', params.slug)
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