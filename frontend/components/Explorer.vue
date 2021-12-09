<template lang="pug">
.pt-2(
  v-infinite-scroll='loadMore',
  infinite-scroll-immediate-check='false',
  infinite-scroll-disabled='loading',
  infinite-scroll-distance=100
)
  .album.py-1.bg-light
    .px-3
      .row
        .col
          .container.p-2.text-right.align-middle
            | Order by:
        .col
          .container.p-1.pb-3 
            b-form-select(
              text='Order by',
              v-model='ordering',
              :options='ordering_options',
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
                  small.text-muted Published: <br/>{{ $myFormatDate(video.snippet.publishedAt) }}
                  small.text-muted Duration: <br/>{{ new Date(video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
        .col-md-4(v-if='loading')
          .card.mb-4.shadow-sm.text-center 
            Loading
</template>

<script >
import LazyHydrate from 'vue-lazy-hydration'
import Loading from '~/components/Loading.vue'
import { Mutex } from 'async-mutex'

export default {
  name: 'Explorer',
  components: {
    LazyHydrate,
    Loading,
  },
  data: () => {
    return {
      logs: [],
      mutex: new Mutex(),
      loading: false,
      query_cursor: null,
      no_more_data: false,
      videos: {},
      // period_options: [
      //   {
      //     text: 'Last week',
      //     value: sub(new Date(), { weeks: 1 }),
      //   },
      //   {
      //     text: 'Last month',
      //     value: sub(new Date(), { months: 1 }),
      //   },
      //   {
      //     text: 'Last year',
      //     value: sub(new Date(), { years: 1 }),
      //   },
      //   {
      //     text: 'Always',
      //     value: null,
      //   },
      // ],
      // start_date: null,
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
  beforeCreate: function () {},
  created: function () {
    // this.logs.push('created')
  },
  beforeMount: function () {
    // this.logs.push('beforeMount')
  },
  mounted: function () {
    // this.logs.push('mounted')
  },
  beforeUpdate: function () {
    // this.logs.push('beforeUpdate')
  },
  beforeUpdate: function () {
    // // this.logs.push('updated')
  },
  beforeUnmount: function () {
    // this.logs.push('beforeUnmount')
  },
  unmounted: function () {
    // this.logs.push('unmounted')
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
    async loadMore() {
      // this.logs.push('loadMore')
      await this.doQuery()
    },
    async handleChange() {
      // if (this.ordering != 'snippet.publishedAt') this.start_date = null
      // this.logs.push('handling change')
      this.query_cursor = null
      this.no_more_data = false
      for (var key in this.videos) {
        // this check can be safely omitted in modern JS engines
        // if (obj.hasOwnProperty(key))
        delete this.videos[key]
      }
      await this.doQuery()
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
      if (this.no_more_data) return
      this.loading = true
      var self = this
      const PAGE_SIZE = 20
      // this.logs.push('--- doQuery ----')

      if (!(this.mutex instanceof Mutex)) this.mutex = new Mutex()
      await this.mutex.runExclusive(async () => {
        // this.logs.push('--- doQuery ---- inside lock')
        //try {

        let query = self.$db.collection('videos')
        if (self.ordering) query = query.orderBy(this.ordering, 'desc')

        if (self.category) {
          query = query.where(
            'videosdb.playlists',
            'array-contains',
            self.category['id']
          )
        }

        // if (this.start_date) {
        //   query = query.where('snippet.publishedAt', '>', this.start_date)
        // }

        if (self.tag)
          query = query.where('snippet.tags', 'array-contains', self.tag)

        let video_count = Object.keys(self.videos).length
        if (!self.query_cursor && video_count) {
          let limit = video_count + PAGE_SIZE
          query = query.limit(limit)
          // this.logs.push('querying for ', limit)
        } else {
          query = query.limit(PAGE_SIZE)
        }

        if (self.query_cursor) {
          query = query.startAfter(self.query_cursor)
          // this.logs.push('aplying cursor')
        }

        let results = await query.get()

        //  Nuxt cant serialize the resulting objects
        if (process.server) {
          self.query_cursor = null
          // this.logs.push('not saving cursor')
        } else {
          self.query_cursor = results.docs.at(-1)
          // this.logs.push('saving cursor')
        }

        results.forEach((doc) => {
          self.$set(self.videos, doc.data().id, doc.data())
        })

        self.no_more_data = results.docs.length < PAGE_SIZE
        // this.logs.push('scroll disabled: ', self.scroll_disabled)
        self.loading = false
      })
    },
  },

  async fetch() {
    // this.logs.push('fetch')
    if (Object.keys(this.videos).length) return
    await this.doQuery()
  },
}
</script>

