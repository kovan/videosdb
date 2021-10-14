//import { registerInterceptor } from 'axios-cached-dns-resolve'

export default function ({$axios}) {
    //registerInterceptor($axios)
    $axios.defaults.timeout = 30000
}