<template lang="pug">
b-container
  Explorer(:current_page='this.$route.params.page || 1', base_url='/')
</template>

<script>


export default {
  head: {
    title: "Sadhguru wisdom",
    meta: [
      {
        hid: 'description',
        name: 'description',
        content: 'Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.'
      }
    ],
  }
}
</script>


<router>
  {
    path: '/:page?'
  }
</router>