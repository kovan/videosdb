import { defineNuxtPlugin } from '#app'
import { createDb } from "~/utils/utils"



var db = null

export default defineNuxtPlugin(nuxtApp => {
    if (!db) {
        db = createDb(nuxtApp.$config.firebase)
    }
    nuxtApp.provide('db', db)
    // now available on `nuxtApp.$injected`
})

