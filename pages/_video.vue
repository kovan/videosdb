<template lang="pug">
v-container
    iframe(
    width='560' 
    height='315' 
    :src="'https:/www.youtube.com/embed/' +this.video.youtube_id"
    frameborder='0' 
    allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture' 
    allowfullscreen)

</template>
<script>
import axios from "axios";

export default {
 
  async asyncData({params}) { 
    let video = await axios.get(
       'http://localhost:8000/api/videos/' + params.video
     )

    video = video.data
    return {video}
  }
}
</script>