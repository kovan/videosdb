<template lang="pug">
v-container
    h1.text-center Most viewed videos
    Explorer(ordering="-view_count")

</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {

}
</script>