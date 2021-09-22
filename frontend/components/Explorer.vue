<template lang="pug">
.pt-2
  .album.py-1.bg-light
    .p-3
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
          LazyHydrate(when-visible)
            .card.mb-4.shadow-sm.text-center
              NuxtLink(:to='"/video/" + video.slug')
                b-img-lazy.bd-placeholder-img.card-img-top(
                  :src='video.thumbnails.medium.url',
                  height='180',
                  width='320',
                  :id='video.youtube_id',
                  :alt='video.title',
                  fluid
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
                  small.text-muted Published: {{ new Date(video.yt_published_date).toLocaleDateString() }}
                  small.text-muted Duration: {{ new Date(video.duration_seconds * 1000).toISOString().substr(11, 8) }}
      .overflow-auto(v-if='this.videos.length')
        LazyHydrate(when-visible)
          b-pagination-nav(
            size='lg',
            align='fill',
            :base-url='base_url',
            v-model='current_page',
            :number-of-pages='page_count',
            use-router,
            first-number,
            last-number,
            pills,
            :link-gen='linkGen'
          )
</template>

<script >

import { handleAxiosError } from "~/utils/utils"
import LazyHydrate from 'vue-lazy-hydration';
export default {
  components: {
    LazyHydrate
  },
  data: () => {
    return {
      page_count: 1,
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
    current_page: () => {
      return 1;
    },
    base_url: () => {
      return "/";
    },
    search: () => {
      return "";
    },
    categories: () => {
      return "";
    },
    tags: () => {
      return "";
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
    const url = new URL('/videos/', dummy_root)
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
      let response = await this.$axios.$get(url.href.replace(dummy_root, ""), { progress: true })
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
