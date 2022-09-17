import axios from "axios"


var myaxios = null

export default defineNuxtPlugin((NuxtApp) => {
    const config = useRuntimeConfig()
    if (!myaxios) {
        myaxios = axios.create({
            baseURL: config.app.baseURL,

        })
    }
    return {
        provide: {
            axios: myaxios.default
        }
    }
})
