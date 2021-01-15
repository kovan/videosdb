<template lang="pug">

    v-container.d-flex.child-flex(align='center', fluid=true)
      v-row(align='center' no-gutters)
        v-col(v-for='video in this.videos' :key='video.youtube_id')
          v-card.pa-2(outlined tile)
            NuxtLink(nuxt :to="video.slug")
              | {{video.title}}            
            NuxtLink(nuxt :to="video.slug")
              v-img(:src="video.thumbnails.medium.url" )


</template>

<script>

export default {
  data: () => {
    return {
      videos: []
    }
  },
  props: ["url"],
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
  async fetch() { 
    let response = await this.$axios.$get(this.url)
  
    this.videos = response.results
    
    
    
  }  
}
</script>
