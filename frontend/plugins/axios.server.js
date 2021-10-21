import { createAxios } from "~/utils/utils.server"
var myaxios = null

export default function({ app, $config }, inject) {
    if (!myaxios) {
        myaxios = createAxios($config.baseURL)
    }

    inject("axios", myaxios)
    
}

