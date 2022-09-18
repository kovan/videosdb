import Vue from 'vue'
import vueScrollBehavior from 'vue-scroll-behavior'

export default defineNuxtPlugin((nuxtApp) => {
    nuxtApp.vueApp.use(vueScrollBehavior, {
        router: nuxtApp.vueApp,
        delay: 100

    })
})
