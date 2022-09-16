import axios from "axios"



export default function ({ app, config.public }, inject) {
    let myaxios = axios.create({
        baseURL: config.public.baseURL,

    })
    inject("axios", myaxios)


}

