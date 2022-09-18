import Vue from 'vue'
import infiniteScroll from 'vue-infinite-scroll'

export default defineNuxtPlugin((nuxtApp) => {
    nuxtApp.vueApp.use(infiniteScroll)
})
