<template lang="pug">
b-container.p-0.m-0
  h1.text-center Category: {{ this.category.snippet.title }}
  Explorer(
    :base_url='`/category/${this.$route.params.slug}`',
    :category='this.category'
  )
</template>

<script>
export default {
  head() {
    return {
      title: this.category.snippet.title + ' - ' + this.$config.title,
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

  async asyncData({ $db, params, payload, store, error }) {
    if (payload) {
      store.commit('setInitial', payload.vuex_data)
      return { category: payload.obj }
    }

    const q_category = await $db
      .collection('playlists')
      .where('videosdb.slug', '==', params.slug)
      .get()

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
