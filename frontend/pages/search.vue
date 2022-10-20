<template lang="pug">
div
    h2.text-center Search
    client-only
        .gcse-search
</template>

<script>

export default {
    data() {
        return {
            loaded: false,
        }
    },
    mounted() {
        this.$loadScript(this.$config.cseUrl).then(() => {
            this.loaded = true
        })
    },
    destroyed() {
        this.$unloadScript(this.$config.cseUrl).then(() => {
            this.loaded = false
        })
    },
    head() {
        return {
            title: 'Search' + ' - ' + this.$config.title,
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

<style>

</style>

<router>
  {
    path: '/search'
  }
</router>
