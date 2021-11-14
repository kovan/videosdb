<template lang="pug">
b-container.m-0.p-0.mx-auto
  script(type='application/ld+json', v-html='this.video_json')
  b-card.m-0.p-0
    small
      | Published: {{ new Date(this.video.snippet.publishedAt).toLocaleDateString() }}.
      | Duration: {{ new Date(this.video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }} }}
    .my-4
      h1 {{ this.video.snippet.title }}
      p(align='center')
        client-only
          LazyYoutube(
            :src='`https://www.youtube.com/watch?v=${this.video.id}`'
          )

    .my-4(v-if='this.video.videosdb.descriptionTrimmed')
      strong Description
      p(style='white-space: pre-line') {{ this.video.videosdb.descriptionTrimmed }}

    .my-4(v-if='this.video.categories && this.video.categories.length > 0')
      strong Categories
      ul
        li(v-for='cat in this.video.categories', :key='cat.id')
          NuxtLink(:to='"/category/" + cat.slug')
            | {{ cat.name }}

    .my-4(v-if='this.video.ipfs_hash')
      p(align='center')
        b-link(
          :href='"https://videos.sadhguru.digital/" + encodeURIComponent(this.video.filename)',
          download
        )
          b-button
            | View / Download
      p(align='center') 
        b-link(
          :href='"ipns://videos.sadhguru.digital/" + encodeURIComponent(this.video.filename)'
        )
          b-button
            | View / Download - with &nbsp;
            b-img(
              src='/ipfs-logo-text-128-ice-white.png',
              height='24px',
              alt='IPFS Logo'
            )

      p(align='center')
        | NOTE: to download the videos, right click on the download link and choose "Save as.."

    .my-4(v-if='this.video.snippet.tags && this.video.snippet.tags.length > 0')
      p.text-center
        NuxtLink.p-1(
          :to='"/tag/" + encodeURIComponent(tag)',
          v-for='tag in this.video.snippet.tags',
          :key='tag'
        )
          b-button.mt-2(size='sm', pill)
            | {{ tag }}

    .my-4(
      v-if='this.video.related_videos && this.video.related_videos.length > 0'
    )
      p
        h2 Related videos:
      .album.py-1.bg-light
        .row
          .col-md-4(
            v-for='related in this.video.related_videos',
            :key='related.id'
          )
            LazyHydrate(when-visible)
              .card.mb-4.shadow-sm.text-center
                NuxtLink(:to='"/video/" + related.slug')
                  b-img-lazy.bd-placeholder-img.card-img-top(
                    :src='related.thumbnails.medium.url',
                    height='180',
                    width='320',
                    :id='related._id',
                    :alt='related.title',
                    fluid
                  )
                  b-popover(
                    :target='related.id',
                    triggers='hover focus',
                    :content='this.video.videosdb.descriptionTrimmed'
                  )
                .card-body
                  p.card-text
                    NuxtLink(:to='"/video/" + related.slug')
                      | {{ related.title }}
                  .d-flex.justify-content-between.align-items-center
                    small.text-muted Published: {{ new Date(related.snippet.publishedAt).toLocaleDateString() }}
                    small.text-muted Duration: {{ new Date(related.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}

    .my-4(v-if='this.video.transcript')
      p
        strong Transcription:
      p(style='white-space: pre-line') {{ this.video.transcript }}
</template>
<script>
import { handleAxiosError } from '~/utils/utils.client'

import LazyHydrate from 'vue-lazy-hydration'

export default {
  components: {
    LazyHydrate,
  },
  head() {
    return {
      title: this.video.title + ' - ' + 'Sadhguru wisdom',
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: this.video.videosdb.descriptionTrimmed,
        },
      ],
    }
  },
  data() {
    return {
      video: {},
    }
  },
  computed: {
    video_json: function () {
      let json = {
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        name: this.video.snippet.title,
        description: this.video.videosdb.descriptionTrimmed,
        thumbnailUrl: Object.values(this.video.snippet.thumbnails).map(
          (thumb) => thumb.url
        ),
        uploadDate: this.video.snippet.publishedAt,
        duration: this.video.contentDetails.duration,
        embedUrl: `https://www.youtube.com/watch?v=${this.video.id}`,
      }
      if ('filename' in this.video)
        json.contentUrl =
          'https://videos.sadhguru.digital/' +
          encodeURIComponent(this.video.filename)
      else json.contentUrl = this.$nuxt.$route.currentRoute

      return JSON.stringify(json)
    },
  },
  methods: {},
  async asyncData({ $fire, params, error }) {
    try {
      const query_results = await $fire.firestore
        .collection('videos')
        .where('videosdb.slug', '==', params.slug)
        .get()

      let video = query_results.docs[0].data()
      return { video }

      // try {
      //   var url = '/videos/' + params.slug + '/'
      //   let video = (await $axios.get(url)).data
      //   return { video }
    } catch (exception) {
      console.error(exception)
      error({ statusCode: null, message: exception.toString() })
    }
  },
}
</script>


<router>
  {
    path: '/video/:slug'
  }
</router>