<template lang="pug">
b-container.p-0.m-0
    h1.text-center Category: {{ this.category.snippet.title }}
    Explorer(
        :base_url='`/category/${this.$route.params.slug}`',
        :category='this.category'
    )
</template>

<script>
import {
    getDoc,
    getDocs,
    limit,
    orderBy,
    where,
    startAfter,
    doc,
    query, collection
} from 'firebase/firestore/lite'


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


        const q_category = query(collection($db, "playlists"), where('videosdb.slug', '==', params.slug))
        let result = await getDocs(q)
        let category = result.docs[0].data()
        return { category }
    },
}
</script>

<router>
  {
    path: '/category/:slug'
  }
</router>
