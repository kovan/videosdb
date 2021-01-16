<template lang="pug">
v-container
    h1.text-center Most commented videos
    Explorer(ordering="-comment_count")

</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {

}
</script>