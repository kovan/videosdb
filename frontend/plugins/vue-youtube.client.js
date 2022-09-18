import Vue from 'vue'
import LazyTube from "vue-lazytube";

export default defineNuxtPlugin((nuxtApp) => {
    nuxtApp.vueApp.use(LazyTube)
})
