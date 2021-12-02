<template lang="pug">
b-container.m-0.p-0.mx-auto
  script(type='application/ld+json', v-html='this.video_json')
  b-card.m-0.p-0
    .my-4
      h1 {{ this.video.snippet.title }}
      p(align='center')
        client-only
          LazyYoutube(
            :src='`https://www.youtube.com/watch?v=${this.video.id}`'
          )
      small
        | Published: {{ formatDate(this.video.snippet.publishedAt) }}.
        | Duration: {{ new Date(this.video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
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
      strong Categories
      ul
        li(v-for='category in this.video.categories', :key='category.id')
          NuxtLink(:to='"/category/" + category.videosdb.slug')
            | {{ category.snippet.title }}

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
      v-if='this.video.videosdb.related_videos && this.video.videosdb.related_videos.length > 0'
    )
      p
        h2 Related videos:
      .album.py-1.bg-light
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
                    NuxtLink(:to='"/video/" + related.slug')
                      | {{ related.title }}
                  .d-flex.justify-content-between.align-items-center
                    small.text-muted Published: {{ formatDate(related.snippet.publishedAt) }}
                    small.text-muted Duration: {{ new Date(related.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}

    .my-4(v-if='this.video.videosdb.transcript')
      p
        strong Transcription:
      p(style='white-space: pre-line') {{ this.video.videosdb.transcript }}
</template>
<script>
import LazyHydrate from 'vue-lazy-hydration'
import { formatDate, getWithCache } from '~/utils/utils'
import { formatISO } from 'date-fns'

export default {
  components: {
    LazyHydrate,
  },
  head() {
    return {
      title: this.video.snippet.title + ' - ' + 'Sadhguru wisdom',
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
          href: `https://www.sadhguru.digital/video/${this.video.videosdb.slug}`,
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
        description: this.video.videosdb.descriptionTrimmed
          ? this.video.videosdb.descriptionTrimmed
          : this.video.snippet.title,
        thumbnailUrl: Object.values(this.video.snippet.thumbnails).map(
          (thumb) => thumb.url
        ),
        uploadDate:
          typeof this.video.snippet.publishedAt == 'object'
            ? formatISO(this.video.snippet.publishedAt.toDate())
            : this.video.snippet.publishedAt,
        duration: this.video.contentDetails.duration,
      }
      let url = null
      if ('filename' in this.video.videosdb) {
        url =
          'https://videos.sadhguru.digital/' +
          encodeURIComponent(this.video.videosdb.filename)
      } else {
        url = `https://www.sadhguru.digital/video/${this.video.videosdb.slug}`
      }
      json.contentUrl = url
      json.embedUrl = url

      let string = JSON.stringify(json)
      return string
    },
  },
  methods: {
    formatDate: function (date) {
      return formatDate(date)
    },
  },
  async asyncData({ $db, params, payload, error, store }) {
    let video = null
    if (payload) {
      video = payload.obj
      store.commit('setInitial', payload.vuex_data)
    } else {
      const q = await getWithCache(
        $db.collection('videos').where('videosdb.slug', '==', params.slug)
      )
      video = q.docs[0].data()
    }

    if ('playlists' in video.videosdb && video.videosdb.playlists.length) {
      const results = await getWithCache(
        $db.collection('playlists').where('id', 'in', video.videosdb.playlists)
      )
      let categories = []
      results.forEach((doc) => {
        categories.push(doc.data())
      })
      video.categories = categories
    }

    if (
      'related_videos' in video.videosdb &&
      video.videosdb.related_videos.length
    ) {
      const results = await getWithCache(
        $db
          .collection('videos')
          .where('id', 'in', video.videosdb.related_videos)
      )
      let related_videos = []
      results.forEach((doc) => {
        related_videos.push(doc.data())
      })
      video.videosdb.related_videos = related_videos
    }

    return { video }
  },
}
</script>


<router>
  {
    path: '/video/:slug'
  }
</router>
