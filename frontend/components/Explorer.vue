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
          .container.p-1.pb-3
            | Period:
            b-form-select(
              text='Period',
              v-model='period',
              :options='period_options',
              @change='handleChange'
            )
      .row(v-if='this.videos.length')
        .col-md-4(v-for='video in this.videos', :key='video.data().id')
          LazyHydrate(when-visible)
            .card.mb-4.shadow-sm.text-center
              NuxtLink(:to='"/video/" + video.data().videosdb.slug')
                b-img-lazy.bd-placeholder-img.card-img-top(
                  :src='video.data().snippet.thumbnails.medium.url',
                  height='180',
                  width='320',
                  :id='video.data().id',
                  :alt='video.data().snippet.title',
                  fluid
                )
                b-popover(
                  :target='video.data().id',
                  triggers='hover focus',
                  :content='video.data().videosdb.descriptionTrimmed'
                )
              .card-body
                p.card-text
                  NuxtLink(:to='"/video/" + video.data().videosdb.slug')
                    | {{ video.data().snippet.title }}
                .d-flex.justify-content-between.align-items-center
                  small.text-muted Published: <br/>{{ $moment(video.data().snippet.publisheAt).format("MMM Do YYYY") }}
                  small.text-muted Duration: <br/>{{ new Date(video.data().videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
</template>

<script >
import LazyHydrate from 'vue-lazy-hydration'

export default {
  components: {
    LazyHydrate,
  },
  data: () => {
    return {
      page_count: 1,
      current_page: 1,
      scroll_disabled: false,
      videos: [],
      period_options: [
        {
          text: 'Last week',
          value: 'last_week',
        },
        {
          text: 'Last month',
          value: 'last_month',
        },
        {
          text: 'Last year',
          value: 'last_year',
        },
        {
          text: 'Always',
          value: 'always',
        },
      ],
      period: 'always',
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
    initial_page: function () {
      return 1
    },
  },

  watch: {
    $route(to, from) {
      this.current_page = this.$route.query.page || 1
      this.$fetch()
    },
  },
  created() {
    this.current_page = this.$route.query.page || this.initial_page
  },
  methods: {
    linkGen(pageNum) {
      return {
        path: this.$route.path,
        query: {
          page: pageNum,
        },
      }
    },
    // infiniteHandler($state) {
    //   console.log('Page: ' + this.current_page)
    //   this.$fetch()
    //   if (this.scroll_finished) $state.complete()
    //   else $state.loaded()
    // },
    async loadMore() {
      console.log('loading more')

      await this.$fetch()
    },
    handleChange() {
      this.fetch()
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
    //     if (video.data().thumbnails.hasOwnProperty(res)) {
    //       srcset += `${video.data().thumbnails[res].url} ${resolutions[res]}w, `
    //       sizes += `(max-width: ${resolutions[res]}px) ${resolutions[res]}px, `
    //     }
    //   }
    //   return [srcset.slice(0, -2), sizes.slice(0, -2)]
    // }
  },
  async fetch() {
    console.log('fetch')
    const PAGE_SIZE = 20
    try {
      let query = this.$fire.firestore
        .collection('videos')
        .limit(PAGE_SIZE)
        .orderBy(this.ordering, 'desc')

      if (this.category) {
        console.debug(this.category)

        query = query.where(
          'videosdb.playlists',
          'array-contains',
          this.category
        )
      }

      if (this.videos.length > 0) {
        query = query.startAfter(this.videos.at(-1))
      }

      //if (this.period) query = query.where('snippet.publishedAt')

      if (this.tag)
        query = query.where('snippet.tags', 'array-contains', this.tag)

      let [results] = await Promise.all([query.get()])

      console.log('LEN: ' + results.docs.length)
      console.log(results)

      results.forEach((doc) => {
        this.videos.push(doc)
      })

      this.scroll_disabled = results.docs.length < PAGE_SIZE
    } catch (exception) {
      console.error(exception)
      this.$nuxt.context.error({
        statusCode: null,
        message: exception.toString(),
      })
    }

    // const dummy_root = 'http://example.com' // otherwise URL doesn't work
    // const url = new URL('/videos/', dummy_root)
    // if (this.ordering) url.searchParams.append('ordering', this.ordering)
    // if (this.period) url.searchParams.append('period', this.period)
    // if (this.current_page > 1)
    //   url.searchParams.append('page', this.current_page)
    // if (this.categories) url.searchParams.append('categories', this.categories)
    // if (this.tags) url.searchParams.append('tags', this.tags)
    // if (this.search) url.searchParams.append('search', this.search)

    // try {
    //   let response = await this.$axios.get(url.href.replace(dummy_root, ''))
    //   this.videos = response.data.results
    //   this.page_count =
    //     response.data.count == 0
    //       ? 0
    //       : Math.floor(response.data.count / response.data.results.length)
    // } catch (exception) {
    //   handleAxiosError(exception, this.$nuxt.context.error)
    // }
  },
}
</script>

