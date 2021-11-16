<template lang="pug">
b-container.p-0.m-0
  h1.text-center Tag: {{ this.$route.params.slug }}
  Explorer(
    :initial_page='this.$route.params.page || 1',
    :base_url='`/tag/${this.$route.params.slug}`',
    :tag='this.$route.params.slug'
  )
</template>

<script>
export default {
  head() {
    return {
      title: this.$route.params.slug + ' - Sadhguru wisdom',
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: 'Tag: ' + this.$route.params.slug,
        },
      ],
    }
  },
  data: () => {
    return {
      tag: '',
    }
  },
}
</script>

<router>
  {
    path: '/tag/:slug'
  }
</router>