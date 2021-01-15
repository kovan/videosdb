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
import Logo from '~/components/Logo.vue'
import VuetifyLogo from '~/components/VuetifyLogo.vue'
import axios from "axios";

export default {
  components: {
    Logo,
    VuetifyLogo
  },
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
  async asyncData() { 
    let videos = await axios.get(
       'http://localhost:8000/api/videos/')

    videos = videos.data.results
    
    return {videos}
  }
}
</script>
