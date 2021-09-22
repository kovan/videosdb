<template lang="pug">
b-container.m-0.p-0.mx-auto
  b-card.m-0.p-0
    small
      | Published: {{ new Date(this.video.yt_published_date).toLocaleDateString() }}.
      | Duration: {{ new Date(this.video.duration_seconds * 1000).toISOString().substr(11, 8) }}
    .my-4
      h1 {{ this.video.title }}
      p(align='center')
        client-only
          youtube(
            :video-id='this.video.youtube_id',
            ref='youtube',
            resize='true',
            fitParent,
            resizeDelay=0
          )

    .my-4(v-if='this.video.description_trimmed')
      h6 Description
      p(style='white-space: pre-line') {{ this.video.description_trimmed }}

    .my-4(v-if='this.video.ipfs_hash')
      p(align='center')
        b-link(
          :href='"https://ipfs.sadhguru.digital/ipfs/" + this.video.ipfs_hash + "?filename=" + encodeURIComponent(this.video.filename)',
          download
        )
          b-button
            | View / Download
        | &nbsp;
        b-link(
          :href='"ipns://videos.sadhguru.digital/" + encodeURIComponent(this.video.filename)'
        )
          b-button
            | View / Download - with &nbsp;
            b-img(src='/ipfs-logo-text-128-ice-white.png', height='24px')
        p(align='center')
          | NOTE: to download the videos, right click on the download link and choose "Save as.."

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
      p(style='white-space: pre-line') {{ this.video.transcript }}
</template>
<script>


import { handleAxiosError } from "~/utils/utils"


export default {
  head () {
    return {
      title: this.video.title + " - " + "Sadhguru wisdom",
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
      video: {}
    }
  },
  async asyncData ({ $axios, params, error }) {

    try {
      var url = '/videos/' + params.slug + "/"
      let video = await $axios.$get(url)
      return { video }
    } catch (exception) {
      handleAxiosError(exception, error)
    }
  }
}
</script>


<router>
  {
    path: '/video/:slug'
  }
</router>