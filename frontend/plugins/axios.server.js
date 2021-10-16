import axios from "axios"

import { config, registerInterceptor } from 'axios-cached-dns-resolve'
import { setupCache } from 'axios-cache-adapter'

export default function({ app, $config }, inject) {
  
    // Create `axios-cache-adapter` instance
    const cache = setupCache({
        maxAge: 60 * 60 * 1000
    })    
    let myaxios = axios.create({
        baseURL: $config.baseURL,
        adapter: cache.adapter
    })
    
    registerInterceptor(myaxios)
    inject("axios", myaxios)
    

}

