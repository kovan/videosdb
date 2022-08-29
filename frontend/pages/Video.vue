<template lang="pug">
b-container.m-0.p-0.mx-auto
  script(type='application/ld+json', v-html='this.video_json')
  b-card.m-0.p-0
    .my-4
      h1 {{ this.video.snippet.title }}
      p
        small
          | Published: {{ $myFormatDate(this.video.snippet.publishedAt) }}.
          | Duration: {{ new Date(this.video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}

      p(align='center')
        client-only
          LazyYoutube(
            :src='`https://www.youtube.com/watch?v=${this.video.id}`'
          )
    .my-4(v-if='this.video.videosdb.descriptionTrimmed')
      strong Description
      p(style='white-space: pre-line') {{ this.video.videosdb.descriptionTrimmed }}

    .my-4(v-if='this.video.videosdb.ipfs_hash')
      p(align='center')
        b-link(
          :href='"https://videos.sadhguru.digital/" + encodeURIComponent(this.video.videosdb.filename)',
          download
        )
          b-button
            | View / Download
      p(align='center')
        b-link(
          :href='"ipns://videos.sadhguru.digital/" + encodeURIComponent(this.video.videosdb.filename)'
        )
          b-button
            | View / Download - with &nbsp;
            b-img(
              src='/ipfs-logo-text-128-ice-white.png',
              height='24px',
              alt='IPFS Logo'
            )

      p(align='center')
        small NOTE: to download the videos, right click on the download link and choose "Save as.."

    .my-4(
      v-if='this.video.videosdb.playlists && this.video.videosdb.playlists.length > 0'
    )
      p
        h2 In categories:
      .album.py-1
        .row
          .col-md-4(
            v-for='item in this.video.videosdb.playlists',
            :key='item.id'
          )
            LazyHydrate(when-visible)
              .card.mb-4.shadow-sm.text-center
                NuxtLink(:to='"/category/" + item.videosdb.slug')
                  b-img-lazy.bd-placeholder-img.card-img-top(
                    :src='item.snippet.thumbnails.medium.url',
                    height='180',
                    width='320',
                    :id='item.id',
                    :alt='item.snippet.title',
                    fluid
                  )
                  b-popover(
                    :target='item.id',
                    triggers='hover focus',
                    :content='item.snippet.description'
                  )
                .card-body
                  p.card-text
                    NuxtLink(:to='"/category/" + item.videosdb.slug')
                      | {{ item.snippet.title }}

    .my-4(
      v-if='this.video.videosdb.related_videos && this.video.videosdb.related_videos.length > 0'
    )
      p
        h2 Related videos:
      .album.py-1
        .row
          .col-md-4(
            v-for='related in this.video.videosdb.related_videos',
            :key='related.id'
          )
            LazyHydrate(when-visible)
              .card.mb-4.shadow-sm.text-center
                NuxtLink(:to='"/video/" + related.videosdb.slug')
                  b-img-lazy.bd-placeholder-img.card-img-top(
                    :src='related.snippet.thumbnails.medium.url',
                    height='180',
                    width='320',
                    :id='related.id',
                    :alt='related.snippet.title',
                    fluid
                  )
                  b-popover(
                    :target='related.id',
                    triggers='hover focus',
                    :content='related.videosdb.descriptionTrimmed'
                  )
                .card-body
                  p.card-text
                    NuxtLink(:to='"/video/" + related.videosdb.slug')
                      | {{ related.snippet.title }}
                  .d-flex.justify-content-between.align-items-center
                    small.text-muted Published: {{ $myFormatDate(related.snippet.publishedAt) }}
                    small.text-muted Duration: {{ new Date(related.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}

    .my-4(v-if='this.video.snippet.tags && this.video.snippet.tags.length > 0')
      p.text-center
        strong Tags:
      p.text-center
        NuxtLink.p-1(
          :to='"/tag/" + encodeURIComponent(tag)',
          v-for='tag in this.video.snippet.tags',
          :key='tag'
        )
          b-button.mt-2(size='sm', pill)
            | {{ tag }}

    .my-4(v-if='this.video.videosdb.transcript')
      p
        strong Transcription:
      small(style='white-space: pre-line') {{ this.video.videosdb.transcript }}
</template>
<script>
import LazyHydrate from 'vue-lazy-hydration'
import { dereferenceDb, videoToStructuredData } from '~/utils/utils'

export default {
  components: {
    LazyHydrate,
  },
  head() {
    return {
      title: this.video.snippet.title + ' - ' + this.$config.subtitle,
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: this.video.videosdb.descriptionTrimmed,
        },
      ],
      link: [
        {
          rel: 'canonical',
          href: `${this.$config.hostname}/video/${this.video.videosdb.slug}`,
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
      return videoToStructuredData(this.video)
    },
  },
  methods: {},
  async asyncData({ $db, params, payload, error, store }) {
    let video = null
    if (payload) {
      video = payload.obj
      store.commit('setInitial', payload.vuex_data)
    } else {
      const q = await $db
        .collection('videos')
        .where('videosdb.slug', '==', params.slug)
        .get()

      video = q.docs[0].data()
    }

    if ('playlists' in video.videosdb && video.videosdb.playlists.length) {
      video.videosdb.playlists = await dereferenceDb(
        video.videosdb.playlists,
        $db.collection('playlists')
      )
    }

    if (
      'related_videos' in video.videosdb &&
      video.videosdb.related_videos.length
    ) {
      video.videosdb.related_videos = await dereferenceDb(
        video.videosdb.related_videos,
        $db.collection('videos')
      )
    }

    return { video }
  },
}
</script>


<router>
  {
    path: '/video/:slug',

  }
</router>
