<template lang="pug">
  
  Explorer(v-bind:videos="this.videos")

</template>

<script>
import Logo from '~/components/Logo.vue'
import Explorer from '~/components/Explorer.vue'
import axios from "axios";

export default {
  data: () => {
    return {
      videos: []
    }
  },
  components: {
    Explorer
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
  async fetch() { 
    let videos = await axios.get(
       'http://localhost:8000/api/videos/')
  
    this.videos = videos.data.results
    
    
  }
}
</script>
