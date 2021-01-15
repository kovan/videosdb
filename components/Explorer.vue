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
  props: ["videos"]
}
</script>
