<template lang="pug">
b-container.p-0.m-0
    h1.text-center Tag: {{ this.$route.params.slug }}
    Explorer(
        :base_url='`/tag/${this.$route.params.slug}`',
        :tag='this.$route.params.slug'
    )
</template>

<script>
definePageMeta({ layout: 'default' })
const config = useRuntimeConfig()
export default {
    head() {
        return {
            title: this.$route.params.slug + ' - ' + config.public.title,
            meta: [
                {
                    hid: 'description',
                    name: 'description',
                    content: 'Tag: ' + this.$route.params.slug,
                },
            ],
        }
    },
    data: () => {
        return {
            tag: '',
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

<router>
  {
    path: '/tag/:slug'
  }
</router>
