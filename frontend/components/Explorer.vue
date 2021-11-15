<template lang="pug">
.pt-2
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
      .row
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
                  small.text-muted Published: <br/>{{ $moment(video.snippet.publisheAt).format("MMM Do YYYY") }}
                  small.text-muted Duration: <br/>{{ new Date(video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
      .overflow-auto(v-if='this.videos.length')
        LazyHydrate(when-visible)
        div
          div(v-for='(item, $index) in videos', :key='$index')
          infinite-loading(
            @infinite='infiniteHandler',
            force-use-infinite-wrapper
          )
</template>

<script >
import { handleAxiosError } from '~/utils/utils.client'
import LazyHydrate from 'vue-lazy-hydration'
import InfiniteLoading from 'vue-infinite-loading'
export default {
  components: {
    LazyHydrate,
    InfiniteLoading,
  },
  data: () => {
    return {
      page_count: 1,
      current_page: 1,
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
    base_url: () => {
      return '/'
    },
    search: () => {
      return ''
    },
    categories: () => {
      return ''
    },
    tag: () => {
      return ''
    },
    initial_page: () => {
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
    infiniteHandler($state) {
      console.log('Page: ' + this.current_page)
      this.$fetch()
      $state.loaded()
    },
    handleChange() {
      this.$fetch()
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
  },
  async fetch() {
    const PAGE_SIZE = 20
    try {
      let query = this.$fire.firestore
        .collection('videos')
        .limit(PAGE_SIZE)
        .orderBy(this.ordering, 'desc')

      //if (this.period) query = query.where('snippet.publishedAt')
      // if (this.categories) url.searchParams.append('categories', this.categories)
      //if (this.tag)
      //query = query.where('snippet.tags', 'array-contains', this.tag)

      //if (this.videos.length > 0) query = query.startAfter(this.videos[-1])

      console.log('Page: ' + this.current_page)
      const meta_query = this.$fire.firestore.collection('meta').doc('meta')

      let [results, meta_results] = await Promise.all([
        query.get(),
        meta_query.get(),
      ])
      console.log('LEN: ' + results.docs.length)
      console.log(results)
      this.videos.length = 0
      results.forEach((doc) => {
        this.videos.push(doc.data())
      })
      const video_count = meta_results.data().videoCount
      this.page_count = Math.floor(video_count / PAGE_SIZE) + 1
      console.log('Page count: ' + this.page_count)
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

