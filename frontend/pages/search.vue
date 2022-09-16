<template lang="pug">
div
    h2.text-center Search
    client-only
        .gcse-search
</template>

<script>
definePageMeta({ layout: 'default' })
const config = useRuntimeConfig()
export default {
    data() {
        return {
            loaded: false,
        }
    },
    mounted() {
        this.$loadScript(config.public.cseUrl).then(() => {
            this.loaded = true
        })
    },
    destroyed() {
        this.$unloadScript(config.public.cseUrl).then(() => {
            this.loaded = false
        })
    },
    head() {
        return {
            title: 'Search' + ' - ' + config.public.title,
            meta: [
                {
                    hid: 'description',
                    name: 'description',
                    content: 'Search',
                },
            ]
        }
    }
}
</script>

<script setup>
//async asyncData({ $db, params, payload, error, store }) {
const { data, pending, error, refresh } = await useAsyncData(null,
    async () => {
        // if (payload) {
        //     store.commit('setInitial', payload.vuex_data)
        // }
    })
</script>


<style>

</style>

<router>
  {
    path: '/search'
  }
</router>
