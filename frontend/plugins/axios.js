export default function ({$axios}) {
    $axios.defaults.timeout = 30000
}