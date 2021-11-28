<template lang="pug">
b-container.p-0.m-0
  keep-alive
    Explorer
</template>

<script>
import Explorer from '~/components/Explorer.vue'
export default {
  components: {
    Explorer,
  },
  head: {
    title: 'Sadhguru wisdom',
    meta: [
      {
        hid: 'description',
        name: 'description',
        content:
          'Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.',
      },
    ],
  },
}
</script>


<router>
  {
    path: '/'
  }
</router>