// In main.js
import Vue from 'vue'
import LoadScript from 'vue-plugin-load-script'

export default defineNuxtPlugin((nuxtApp) => {
    nuxtApp.vueApp.use(LoadScript)
})
