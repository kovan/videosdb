<template lang="pug">
v-container
  v-container.d-flex.child-flex(align='center', fluid)
    v-row(align='center')
      v-col(v-for='video in this.videos', :key='video.youtube_id')
        v-card.pa-2(outlined, tile)
          NuxtLink(  :to='"/" + video.slug')
            | {{ video.title }}
          NuxtLink(  :to='"/" + video.slug')
            v-img(:src='video.thumbnails.medium.url')
  v-pagination(
    v-model='current_page',
    :length='page_count',
    @input='handlePageChange'
  )
</template>

<script>
export default {
  data: () => {
    return {
      videos: [],
      current_page: 1,
      page_count: 0,
    }
  },
  props: {
    ordering: {
      default: '',
      type: String,
    },
    categories: {
      default: ''
    },
    tags: {
      default: ''
    },    
  },

  methods: {
    handlePageChange (value) {
      this.currentPage = value
      this.$fetch()
      // this.$router.push({
      //   path: ""
      // })
    },
  },
  async fetch () {
    let url = '/api/videos/?'
    if (this.ordering)
      url += `&ordering=${this.ordering}&page=${this.current_page}`
    if (this.categories) 
      url += `&categories=${this.categories}`
    if (this.tags) 
      url += `&tags=${this.tags}`

    let response = await this.$axios.$get(url)
    this.videos = response.results
    
    this.page_count = Math.floor(response.count / response.results.length)
  },
}
</script>
