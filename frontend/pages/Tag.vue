<template lang="pug">
b-container.p-0.m-0
    h1.text-center Tag: {{ this.$route.params.slug }}
    Explorer(
        :base_url='`/tag/${this.$route.params.slug}`',
        :tag='this.$route.params.slug'
    )
</template>

<script>
export default {
    head() {
        return {
            title: this.$route.params.slug + ' - ' + this.$config.title,
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
    },
    async asyncData({ payload, store }) {
        if (payload) {
            store.commit('setInitial', payload.vuex_data)
        }
    },
}
</script>

