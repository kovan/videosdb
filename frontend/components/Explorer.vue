<template lang="pug">
.pt-2(v-infinite-scroll='loadMore', infinite-scroll-disabled='scroll_disabled')
  .album.py-1.bg-light
    .px-3
      .row
        .col
          .container.p-1.pb-3
            | Order by:
            b-form-select(
              text='Order by',
              v-model='ordering',
              :options='ordering_options',
              @change='handleChange'
            )
        .col
          .container.p-1.pb-3(v-if='ordering == "snippet.publishedAt"')
            | Period:
            b-form-select(
              text='Period',
              v-model='start_date',
              :options='period_options',
              @change='handleChange'
            )
      .row(v-if='Object.keys(this.videos).length')
        .col-md-4(v-for='video in this.videos', :key='video.id')
          LazyHydrate(when-visible)
            .card.mb-4.shadow-sm.text-center
              NuxtLink(:to='"/video/" + video.videosdb.slug')
                b-img-lazy.bd-placeholder-img.card-img-top(
                  :src='video.snippet.thumbnails.medium.url',
                  height='180',
                  width='320',
                  :id='video.id',
                  :alt='video.snippet.title',
                  fluid
                )
                b-popover(
                  :target='video.id',
                  triggers='hover focus',
                  :content='video.videosdb.descriptionTrimmed'
                )
              .card-body
                p.card-text
                  NuxtLink(:to='"/video/" + video.videosdb.slug')
                    | {{ video.snippet.title }}
                .d-flex.justify-content-between.align-items-center
                  small.text-muted Published: <br/>{{ formatDate(video.snippet.publishedAt) }}
                  small.text-muted Duration: <br/>{{ new Date(video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
</template>

<script >
import LazyHydrate from 'vue-lazy-hydration'
import { parseISO, sub } from 'date-fns'
import { formatDate, getWithCache } from '~/utils/utils'

export default {
  name: 'Explorer',
  components: {
    LazyHydrate,
  },
  data: () => {
    return {
      query_cursor: null,
      from_ssr: false,
      current_page: 1,
      scroll_disabled: false,
      videos: {},
      period_options: [
        {
          text: 'Last week',
          value: sub(new Date(), { weeks: 1 }),
        },
        {
          text: 'Last month',
          value: sub(new Date(), { months: 1 }),
        },
        {
          text: 'Last year',
          value: sub(new Date(), { years: 1 }),
        },
        {
          text: 'Always',
          value: null,
        },
      ],
      start_date: null,
      ordering_options: [
        {
          text: 'Latest',
          value: 'snippet.publishedAt',
        },
        {
          text: 'Most viewed',
          value: 'statistics.viewCount',
        },
        {
          text: 'Most liked',
          value: 'statistics.likeCount',
        },
        {
          text: 'Most commented',
          value: 'statistics.commentCount',
        },
        {
          text: 'Most favorited',
          value: 'statistics.favoriteCount',
        },
      ],
      ordering: 'snippet.publishedAt',
    }
  },
  props: {
    base_url: function () {
      return '/'
    },
    search: function () {
      return ''
    },
    category: function () {
      return ''
    },
    tag: function () {
      return ''
    },
  },

  // watch: {
  //   '$route.query': '$fetch',
  //   // $route(to, from) {
  //   //   this.current_page = this.$route.query.page || 1
  //   //   this.$fetch()
  //   // },
  // },
  // created() {
  //   this.current_page = this.$route.query.page || this.initial_page
  // },
  methods: {
    formatDate: function (date) {
      return formatDate(date)
    },

    async loadMore() {
      await this.doQuery()
    },
    handleChange() {
      if (this.ordering != 'snippet.publishedAt') this.start_date = null

      this.query_cursor = null
      for (var key in this.videos) {
        // this check can be safely omitted in modern JS engines
        // if (obj.hasOwnProperty(key))
        delete this.videos[key]
      }
      this.doQuery()
    },

    // getSrcSetAndSizes (video) {
    //   let srcset = ""
    //   let sizes = ""
    //   const resolutions = {
    //     default: 120,
    //     medium: 320,
    //     high: 480,
    //     standard: 640
    //   }
    //   for (const res in resolutions) {
    //     if (video.thumbnails.hasOwnProperty(res)) {
    //       srcset += `${video.thumbnails[res].url} ${resolutions[res]}w, `
    //       sizes += `(max-width: ${resolutions[res]}px) ${resolutions[res]}px, `
    //     }
    //   }
    //   return [srcset.slice(0, -2), sizes.slice(0, -2)]
    // }
    async doQuery() {
      const PAGE_SIZE = 20
      try {
        let query = this.$db.collection('videos')
        if (this.ordering) query = query.orderBy(this.ordering, 'desc')

        if (this.category) {
          query = query.where(
            'videosdb.playlists',
            'array-contains',
            this.category['id']
          )
        }

        if (this.start_date) {
          query = query.where('snippet.publishedAt', '>', this.start_date)
        }

        if (this.tag)
          query = query.where('snippet.tags', 'array-contains', this.tag)

        if (this.from_ssr) {
          query = query.limit(PAGE_SIZE * 2)
          this.from_ssr = false
        } else {
          query = query.limit(PAGE_SIZE)
        }

        if (this.query_cursor) {
          query = query.startAfter(this.query_cursor)
        }

        let results = await getWithCache(query)

        //  Nuxt cant serialize the resulting objects
        if (process.server) this.from_ssr = true
        else this.query_cursor = results.docs.at(-1)

        results.forEach((doc) => {
          this.$set(this.videos, doc.data().id, doc.data())
        })

        this.scroll_disabled = results.docs.length < PAGE_SIZE
      } catch (e) {
        console.log(e)
      }
    },
  },

  async fetch() {
    this.doQuery()
  },
}
</script>

