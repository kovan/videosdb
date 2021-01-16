<template lang="pug">
  
  Explorer(:categories="this.category_id" ordering="-favorite_count")

</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  asyncData(context) {
    return { category_id: context.query.id }
  }
}
</script>