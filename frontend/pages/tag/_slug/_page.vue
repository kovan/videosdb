<template lang="pug">
b-container
  Explorer(
    :current_page='this.$route.params.page',
    :base_url='`/tag/${this.$route.params.slug}/`',
    :tag='this.$route.slug'
  )
</template>

<script>


export default {
}

</script>

<style>
</style>
