<template lang="pug">
.pt-2
  .album.py-1.bg-light
    div
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
        .col-md-4(v-for='video in this.videos', :key='video.youtube_id')
          .card.mb-4.shadow-sm.text-center
            NuxtLink(:to='"/video/" + video.slug')
              b-img.bd-placeholder-img.card-img-top(
                :src='video.thumbnails.medium.url',
                width='100%',
                :id='video.youtube_id'
              )
              b-popover(
                :target='video.youtube_id',
                triggers='hover focus',
                :content='video.description_trimmed'
              )
            .card-body
              p.card-text
                NuxtLink(:to='"/video/" + video.slug')
                  | {{ video.title }}
              .d-flex.justify-content-between.align-items-center
                small.text-muted {{ video.yt_published_date.substring(0, 10) }}, {{ video.duration_humanized }}h
      .overflow-auto(v-if='this.videos.length')
        b-pagination-nav(
          size='lg',
          align='center',
          v-model='current_page',
          :link-gen='linkGen',
          :number-of-pages='page_count',
          use-router
        )
</template>

<script >

import { handleAxiosError } from "~/utils/utils"
export default {

  data: () => {
    return {
      page_count: 1,
      current_page: 1,
      videos: [],
      period_options: [
        {
          text: "Last week",
          value: "last_week"
        },
        {
          text: "Last month",
          value: "last_month"
        },
        {
          text: "Last year",
          value: "last_year"
        },
        {
          text: "Always",
          value: "always"
        }
      ],
      period: "always",
      ordering_options: [
        {
          text: "Latest",
          value: "-yt_published_date"
        },
        {
          text: "Most viewed",
          value: "-view_count"
        },
        {
          text: "Most liked",
          value: "-like_count"
        },
        {
          text: "Most commented",
          value: "-comment_count"
        },
        {
          text: "Most favorited",
          value: "-favorite_count"
        }
      ],
      ordering: "-yt_published_date"
    }
  },
  props: {
    search: "",
    categories: {
      default: ''
    },
    tags: {
      default: ''
    },
  },

  watch: {
    $route (to, from) {
      this.current_page = this.$route.query.page || 1
      this.$fetch()
    }
  },
  methods: {
    linkGen (pageNum) {
      return {
        path: this.$route.path,
        query: {
          page: pageNum
        }
      }
    },

    handleChange () {
      this.$fetch()
    }
  },
  async fetch () {


    const dummy_root = "http://example.com"  // otherwise URL doesn't work
    const url = new URL('/api/videos/', dummy_root)
    if (this.ordering)
      url.searchParams.append("ordering", this.ordering)
    if (this.period)
      url.searchParams.append("period", this.period)
    if (this.current_page > 1)
      url.searchParams.append("page", this.current_page)
    if (this.categories)
      url.searchParams.append("categories", this.categories)
    if (this.tags)
      url.searchParams.append("tags", this.tags)
    if (this.search)
      url.searchParams.append("search", this.search)

    try {
      //this.$nuxt.$loading.start() //STARTS LOADING
      let response = await this.$axios.$get(url.href.replace(dummy_root, ""), { progress: true })
      //this.$nuxt.$loading.finish() //STOPS LOADING
      this.videos = response.results
      this.page_count = response.count == 0 ? 0 : Math.floor(response.count / response.results.length)
    } catch (exception) {
      handleAxiosError(exception, this.$nuxt.context.error)
    }

  },
}
</script>


<style scoped>
</style>
