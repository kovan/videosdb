<template lang="pug">
v-container
    h1.text-center Most favorited videos
    Explorer(ordering="-favorite_count")

</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {

}
</script>