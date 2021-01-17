<template lang="pug">
v-container.ma-0.pa-0(align='center', v-if="this.videos.length")
  v-container(fluid)
    v-row(align='center')
      v-col.d-flex
        v-select(
          :items='ordering_options',
          label='Order by ',
          @change='handleOrderingChange'
        )
        v-text-field(
          v-model='search',
          hide-details,
          prepend-icon='mdi-magnify',
          single-line,
          label='Search...',
          clearable,
          @change='handleSearch'
        )

  v-container.ma-0.pa-0.d-flex.child-flex(align='center')
    v-row.ma-0.pa-0(justify='center')
      v-col(v-for='video in this.videos', :key='video.youtube_id', no-gutters)
        v-card.pa-0.ma-0(no-gutters, outlined, shaped, tile, elevation='20')
          v-card-title(align='center')
            NuxtLink(nuxt, :to='"/video/" + video.slug')
              | {{ video.title }}
          v-card-text
            NuxtLink(nuxt, :to='"/video/" + video.slug')
              v-img(:src='video.thumbnails.medium.url')
          v-card-text(style='white-space: pre-line')
            | {{ video.description_trimmed }}

  v-pagination(
    v-model='current_page',
    :length='page_count',
    @input='handlePageChange'
  )
v-container(v-else)
  | No videos found.
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
    const dummy_root = "http://example.com"  // otherwise URL doesn't work
    const url = new URL('/api/videos/', dummy_root)
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

    try {
      let response = await this.$axios.$get(url.href.replace(dummy_root, ""))
      this.videos = response.results
      this.page_count = Math.floor(response.count / response.results.length)

    } catch (error) {
      console.error(error)
    }

  },
}
</script>
