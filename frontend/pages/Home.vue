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
            title: this.$config.title,
            meta: [
                {
                    hid: 'description',
                    name: 'description',
                    content:
                        this.$config.subtitle,
                },
            ],
        }
    },
    async asyncData({ payload, store }) {
        if (payload) {
            store.commit('setInitial', payload.vuex_data)
        }
    },
}
</script>

