<template lang="pug">
v-container
  v-container(fluid)
    v-row(align='center')
      v-col.d-flex
        v-select(
          :items='ordering_options',
          label='Order by ',
          @change='handleOrderingChange'
        )
        v-text-field(
          v-model="search"
          hide-details,
          prepend-icon='mdi-magnify',
          single-line,
          label='Type to filter videos',
          clearable,
          @change='handleSearch'
        )

  v-container.d-flex.child-flex(align='center', fluid)
    v-row(align='center')
      v-col(v-for='video in this.videos', :key='video.youtube_id')
        v-card.pa-2(outlined, tile)
          NuxtLink(nuxt, :to='"/video/" + video.slug')
            | {{ video.title }}
          NuxtLink(nuxt, :to='"/video/" + video.slug')
            v-img(:src='video.thumbnails.medium.url')
  v-pagination(
    v-model='current_page',
    :length='page_count',
    @input='handlePageChange'
  )
</template>

<script>
export default {
  data: () => {
    return {
      videos: [],
      current_page: 1,
      page_count: 0,
      search: "",
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
        },
      ]
    }
  },
  props: {
    ordering: {
      default: '',
      type: String,
    },
    categories: {
      default: ''
    },
    tags: {
      default: ''
    },
  },

  methods: {
    handlePageChange () {
      this.$fetch()
    },
    handleSearch () {
      this.$fetch()
    },
    handleOrderingChange (args) {
      this.ordering = args
      this.$fetch()
    }
  },
  async fetch () {
    const url = new URL('/api/videos/', "http://localhost:8000")
    if (this.ordering)
      url.searchParams.append("ordering", this.ordering)
    if (this.current_page)
      url.searchParams.append("page", this.current_page)
    if (this.categories)
      url.searchParams.append("categories", this.categories)
    if (this.tags)
      url.searchParams.append("tags", this.tags)
    if (this.search)
      url.searchParams.append("search", this.search)

    let response = await this.$axios.$get(url.href)
    this.videos = response.results

    this.page_count = Math.floor(response.count / response.results.length)
  },
}
</script>
