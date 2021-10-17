import axios from "axios"
import { registerInterceptor } from 'axios-cached-dns-resolve'
import { cacheAdapterEnhancer } from 'axios-extensions';

var myaxios = null

export default function({ app, $config }, inject) {
    if (!myaxios) {
        myaxios = axios.create({
            baseURL: $config.baseURL,
            adapter: cacheAdapterEnhancer(axios.defaults.adapter)

        })

        registerInterceptor(myaxios)
        console.log("Axios caches installed")    

    }

    inject("axios", myaxios)
    
}

