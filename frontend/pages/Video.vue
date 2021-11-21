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
        | Published: {{ this.video.snippet.publishedAt.toDate().toLocaleDateString() }}.
        | Duration: {{ new Date(this.video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
    .my-4(v-if='this.video.videosdb.descriptionTrimmed')
      strong Description
      p(style='white-space: pre-line') {{ this.video.videosdb.descriptionTrimmed }}

    .my-4(
      v-if='this.video.videosdb.playlists && this.video.videosdb.playlists.length > 0'
    )
      strong Categories
      ul
        li(
          v-for='playlist in this.video.videosdb.playlists',
          :key='playlist.id'
        )
          NuxtLink(:to='"/category/" + playlist.videosdb.slug')
            | {{ playlist.snippet.title }}

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
                    :src='related.thumbnails.medium.url',
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
                    small.text-muted Published: {{ related.snippet.publishedAt.toDate().toDateString() }}
                    small.text-muted Duration: {{ new Date(related.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}

    .my-4(v-if='this.video.videosdb.transcript')
      p
        strong Transcription:
      p(style='white-space: pre-line') {{ this.video.videosdb.transcript }}
</template>
<script>
import LazyHydrate from 'vue-lazy-hydration'

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
          href: `https://www.sadhguru.digital/video/${this.video.slug}`,
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
        embedUrl: `https://www.sadhguru.digital/video/${this.video.slug}`,
      }
      if ('filename' in this.video.videosdb)
        json.contentUrl =
          'https://videos.sadhguru.digital/' +
          encodeURIComponent(this.video.filename)
      else json.contentUrl = json.embedUrl
      return JSON.stringify(json)
    },
  },
  methods: {},
  async asyncData({ $db, params, error }) {
    try {
      const q_videos = await $db
        .collection('videos')
        .where('videosdb.slug', '==', params.slug)
        .get()

      let video = q_videos.docs[0].data()
      console.debug(video.id)
      return { video }
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
