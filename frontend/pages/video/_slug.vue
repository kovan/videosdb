<template lang="pug">
b-container.m-0.p-0.mx-auto
  b-card.m-0.p-0(:title='this.video.title')
    .my-4
      b-embed(
        type='iframe',
        aspect='16by9',
        :src='"https://www.youtube.com/embed/" + this.video.youtube_id + "?rel=0"',
        allowfullscreen
      )

    .my-4(v-if='this.video.description_trimmed')
      h6 Description
      p {{ this.video.description_trimmed }}

    .my-4(v-if='this.video.ipfs_hash')
      h6 Download
      ul
        li
          a(
            :href='"https://ipfs." + $config.domain + "/ipfs/" + this.video.ipfs_hash + "?filename=" + this.video.filename',
            download
          ) Using HTTP (standard)
        li
          a(
            :href='"ipfs://" + this.video.ipfs_hash + "?filename=" + this.video.filename'
          ) Using IPFS (experimental)

    .my-4(v-if='this.video.categories')
      h6 Categories
      ul
        li(v-for='cat in this.video.categories', :key='cat.id')
          NuxtLink(:to='"/category/" + cat.slug')
            | {{ cat.name }}

    .my-4(v-if='this.video.tags')
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
      small {{ this.video.transcript }}
</template>
<script>


import handleAxiosError from "~/utils/utils"

export default {
  head () {
    return {
      title: this.video.title,
      meta: [
        {
          hid: "description",
          name: "description",
          content: this.video.description
        }
      ]
    }
  },
  data () {
    return {
      video: {}
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

