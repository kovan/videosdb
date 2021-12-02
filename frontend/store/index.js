import { createDb } from "../utils/utils"
export const state = () => ({
})

export const getters = {}

export const mutations = {
    setInitial(state, i) {

        state.categories = i.categories
        state.meta_data = i.meta_data
    }
}

export const actions = {
    async nuxtServerInit(store, context) {

        const query = context.$db
            .collection('playlists')
            .orderBy('videosdb.lastUpdated', 'desc')

        const meta_query = context.$db.collection('meta').doc('meta')

        let [results, meta_results] = await Promise.all([
            query.get(),
            meta_query.get(),
        ])
        let categories = []
        results.forEach((doc) => {
            let category = {
                name: doc.data().snippet.title,
                slug: doc.data().videosdb.slug,
                use_count: doc.data().videosdb.videoCount,
            }
            categories.push(category)
        })

        let meta_data = meta_results.data()
        console.log('server init')
        store.commit("setInitial", { categories, meta_data })
    }
}