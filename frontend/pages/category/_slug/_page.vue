<template lang="pug">
b-container
  Explorer(
    :current_page='this.$route.params.page',
    :base_url='`/category/${this.$route.params.slug}/`',
    :categories='this.$route.slug'
  )
</template>

<script>


export default {
}

</script>

<style>
</style>
