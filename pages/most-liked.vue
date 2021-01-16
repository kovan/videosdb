<template lang="pug">
v-container
    h1.text-center Most liked videos
    Explorer(ordering="-like_count")

</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {

}
</script>