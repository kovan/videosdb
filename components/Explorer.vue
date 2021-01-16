<template lang="pug">
  v-container
    v-container.d-flex.child-flex(align='center', fluid=true)
      v-row(align='center')
        v-col(v-for='video in this.videos' :key='video.youtube_id')
          v-card.pa-2(outlined tile)
            NuxtLink(nuxt :to="video.slug")
              | {{video.title}}            
            NuxtLink(nuxt :to="video.slug")
              v-img(:src="video.thumbnails.medium.url" )
    v-pagination(v-model="current_page" :length="page_count", @input="handlePageChange")

</template>

<script>

export default {
  data: () => {
    return {
      videos: [],
      current_page: 1,
      page_count: 0
    }
  },
  props: ["ordering"],
  computed: {
    // preparedVideos: function () {
    //   let prepared = this.videos.map( video => {
    //     let thumbs_prepared = ""
        
    //     for (const size in video.thumbnails) {
    //       thumbs_prepared += video.thumbnails[size].url + ", "

    //     }
    //     video.thumbs_prepared = thumbs_prepared;
    //     return video
    //   })
      
    //   return prepared;
    // }
  },
  methods: {
    handlePageChange(value) {
      this.currentPage = value;
      this.$fetch()
      // this.$router.push({
      //   path: ""
      // })
    }
  },  
  async fetch() { 
    let url = `/api/videos/?ordering=${this.ordering}&page=${this.current_page}`
    let response = await this.$axios.$get(url)
    this.videos = response.results
    this.page_count = Math.floor(response.count / response.results.length)

  }  
}
</script>
