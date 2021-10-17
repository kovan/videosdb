import axios from "axios"



export default function({ app, $config }, inject) {
    let myaxios = axios.create({
        baseURL: $config.baseURL,

    })
    inject("axios", myaxios)
    

}

