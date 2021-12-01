<template lang="pug">
.pt-2(v-infinite-scroll='loadMore', infinite-scroll-disabled='scroll_disabled')
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
                  small.text-muted Published: <br/>{{ formatDate(video.snippet.publishedAt) }}
                  small.text-muted Duration: <br/>{{ new Date(video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
        .col-md-4(v-if='loading')
          .card.mb-4.shadow-sm.text-center 
            .sk-fading-circle
              .sk-circle1.sk-circle
              .sk-circle2.sk-circle
              .sk-circle3.sk-circle
              .sk-circle4.sk-circle
              .sk-circle5.sk-circle
              .sk-circle6.sk-circle
              .sk-circle7.sk-circle
              .sk-circle8.sk-circle
              .sk-circle9.sk-circle
              .sk-circle10.sk-circle
              .sk-circle11.sk-circle
              .sk-circle12.sk-circle
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
      loading: false,
      query_cursor: null,
      from_ssr: false,
      current_page: 1,
      scroll_disabled: false,
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
      this.loading = true
      await this.doQuery()
      this.loading = false
    },
    async handleChange() {
      // if (this.ordering != 'snippet.publishedAt') this.start_date = null

      this.query_cursor = null
      for (var key in this.videos) {
        // this check can be safely omitted in modern JS engines
        // if (obj.hasOwnProperty(key))
        delete this.videos[key]
      }
      this.loading = true
      await this.doQuery()
      this.loading = false
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

        // if (this.start_date) {
        //   query = query.where('snippet.publishedAt', '>', this.start_date)
        // }

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
    await this.doQuery()
  },
}
</script>

<style scoped>
.sk-fading-circle {
  margin: 100px auto;
  width: 80px;
  height: 80px;
  position: relative;
}

.sk-fading-circle .sk-circle {
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 0;
}

.sk-fading-circle .sk-circle:before {
  content: '';
  display: block;
  margin: 0 auto;
  width: 15%;
  height: 15%;
  background-color: #333;
  border-radius: 100%;
  -webkit-animation: sk-circleFadeDelay 1.2s infinite ease-in-out both;
  animation: sk-circleFadeDelay 1.2s infinite ease-in-out both;
}
.sk-fading-circle .sk-circle2 {
  -webkit-transform: rotate(30deg);
  -ms-transform: rotate(30deg);
  transform: rotate(30deg);
}
.sk-fading-circle .sk-circle3 {
  -webkit-transform: rotate(60deg);
  -ms-transform: rotate(60deg);
  transform: rotate(60deg);
}
.sk-fading-circle .sk-circle4 {
  -webkit-transform: rotate(90deg);
  -ms-transform: rotate(90deg);
  transform: rotate(90deg);
}
.sk-fading-circle .sk-circle5 {
  -webkit-transform: rotate(120deg);
  -ms-transform: rotate(120deg);
  transform: rotate(120deg);
}
.sk-fading-circle .sk-circle6 {
  -webkit-transform: rotate(150deg);
  -ms-transform: rotate(150deg);
  transform: rotate(150deg);
}
.sk-fading-circle .sk-circle7 {
  -webkit-transform: rotate(180deg);
  -ms-transform: rotate(180deg);
  transform: rotate(180deg);
}
.sk-fading-circle .sk-circle8 {
  -webkit-transform: rotate(210deg);
  -ms-transform: rotate(210deg);
  transform: rotate(210deg);
}
.sk-fading-circle .sk-circle9 {
  -webkit-transform: rotate(240deg);
  -ms-transform: rotate(240deg);
  transform: rotate(240deg);
}
.sk-fading-circle .sk-circle10 {
  -webkit-transform: rotate(270deg);
  -ms-transform: rotate(270deg);
  transform: rotate(270deg);
}
.sk-fading-circle .sk-circle11 {
  -webkit-transform: rotate(300deg);
  -ms-transform: rotate(300deg);
  transform: rotate(300deg);
}
.sk-fading-circle .sk-circle12 {
  -webkit-transform: rotate(330deg);
  -ms-transform: rotate(330deg);
  transform: rotate(330deg);
}
.sk-fading-circle .sk-circle2:before {
  -webkit-animation-delay: -1.1s;
  animation-delay: -1.1s;
}
.sk-fading-circle .sk-circle3:before {
  -webkit-animation-delay: -1s;
  animation-delay: -1s;
}
.sk-fading-circle .sk-circle4:before {
  -webkit-animation-delay: -0.9s;
  animation-delay: -0.9s;
}
.sk-fading-circle .sk-circle5:before {
  -webkit-animation-delay: -0.8s;
  animation-delay: -0.8s;
}
.sk-fading-circle .sk-circle6:before {
  -webkit-animation-delay: -0.7s;
  animation-delay: -0.7s;
}
.sk-fading-circle .sk-circle7:before {
  -webkit-animation-delay: -0.6s;
  animation-delay: -0.6s;
}
.sk-fading-circle .sk-circle8:before {
  -webkit-animation-delay: -0.5s;
  animation-delay: -0.5s;
}
.sk-fading-circle .sk-circle9:before {
  -webkit-animation-delay: -0.4s;
  animation-delay: -0.4s;
}
.sk-fading-circle .sk-circle10:before {
  -webkit-animation-delay: -0.3s;
  animation-delay: -0.3s;
}
.sk-fading-circle .sk-circle11:before {
  -webkit-animation-delay: -0.2s;
  animation-delay: -0.2s;
}
.sk-fading-circle .sk-circle12:before {
  -webkit-animation-delay: -0.1s;
  animation-delay: -0.1s;
}

@-webkit-keyframes sk-circleFadeDelay {
  0%,
  39%,
  100% {
    opacity: 0;
  }
  40% {
    opacity: 1;
  }
}

@keyframes sk-circleFadeDelay {
  0%,
  39%,
  100% {
    opacity: 0;
  }
  40% {
    opacity: 1;
  }
}
</style>
