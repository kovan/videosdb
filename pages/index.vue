<template lang="pug">



  v-container
    v-container.grey.lighten-5.mb-6(align='center', fluid=true)
      v-row(align='center' no-gutters='' style='height: 150px;')
        v-col(v-for='video in this.videos' :key='youtube_id')
          v-card.pa-2(outlined='' tile='')
            //- iframe(
            //-   width='560' 
            //-   height='315' 
            //-   :src="'https:/www.youtube.com/embed/' +video.youtube_id"
            //-   frameborder='0' 
            //-   allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture' 
            //-   allowfullscreen='')

            | {{video.title}}



          v-card-actions
            v-spacer
              v-btn(color='primary' nuxt='' to='/inspire')
                | Continue
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

  async asyncData() { 
    let videos = await axios.get(
       'http://localhost:8000/api/videos/'
     )

    videos = videos.data.results
    
    console.log("Videos2: " +videos)
    return {videos}
  }
}
</script>
