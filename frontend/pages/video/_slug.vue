<template lang="pug">
b-container.m-0.p-0.mx-auto
  b-card.m-0.p-0(:title='this.video.title')
    small
      | Published: {{ new Date(this.video.yt_published_date).toLocaleDateString() }}. Duration: {{ this.video.duration_humanized }}
    .my-4
      b-embed(
        type='iframe',
        aspect='16by9',
        :src='"https://www.youtube.com/embed/" + this.video.youtube_id + "?rel=0"',
        allowfullscreen,
        autoplay
      )

    .my-4(v-if='this.video.description_trimmed')
      h6 Description
      p {{ this.video.description_trimmed }}

    .my-4(v-if='this.video.ipfs_hash')
      h6 Download
      ul
        li
          a(
            :href='"https://videos." + this.config.domain + "/" + encodeURIComponent(this.video.filename)',
            download
          ) Using HTTP (standard)
        li
          a(
            :href='"ipns://videos." + this.config.domain + "/" + encodeURIComponent(this.video.filename)'
          ) Using IPFS (P2P)

    .my-4(v-if='this.video.categories && this.video.categories.length > 0')
      h6 Categories
      ul
        li(v-for='cat in this.video.categories', :key='cat.id')
          NuxtLink(:to='"/category/" + cat.slug')
            | {{ cat.name }}

    .my-4(v-if='this.video.tags && this.video.tags.length > 0')
      h6 Tags
      NuxtLink.p-1(
        :to='"/tag/" + tag.slug',
        v-for='tag in this.video.tags',
        :key='tag.id'
      )
        b-button.mt-2(size='sm', pill)
          | {{ tag.name }}

    .my-4(v-if='this.video.transcript')
      h6 Transcription:
      p {{ this.video.transcript }}
</template>
<script>


import { handleAxiosError, getConfigForRequest } from "~/utils/utils"

export default {
  head () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      title: this.video.title + " - " + config.title,
      meta: [
        {
          hid: "description",
          name: "description",
          content: this.video.description_trimmed
        }
      ]
    }
  },
  data () {
    return {
      video: {},
      config: getConfigForRequest(this.$nuxt.context.req)
    }
  },
  async asyncData ({ $axios, params, error }) {

    try {
      var url = '/api/videos/' + params.slug + "/"
      let video = await $axios.$get(url)
      return { video }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>

<style>
</style>

