<template lang="pug">
b-container.p-0.m-0
    keep-alive
        Explorer
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
    components: {
        Explorer,
    },
    head() {
        return {
            title: config.public.title,
            meta: [
                {
                    hid: 'description',
                    name: 'description',
                    content:
                        config.public.subtitle,
                },
            ],
        }
    }
}
</script>


<script setup>
definePageMeta({ layout: 'default' })
const config = useRuntimeConfig()
//async asyncData({ $db, params, payload, error, store }) {
const { data, pending, error, refresh } = await useAsyncData(null,
    async () => {
        // if (payload) {
        //     store.commit('setInitial', payload.vuex_data)
        // }
    })
</script>

