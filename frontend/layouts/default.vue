<template lang="pug">
div
  b-nav.navbar.navbar-dark.bg-dark.p-2.pl-3.d-flex.align-middle
    NuxtLink.mr-auto.h5.mt-1.text-white.align-middle(to='/') Sadhguru wisdom

    b-button.mx-1(
      squared,
      @click.default='randomVideo()',
      title='Random video',
      style='border: 0px'
    )
      b-icon(icon='shuffle', alt='Random video')

    b-button.mx-1(
      squared,
      @click='hideSidebar',
      to='/search',
      title='Search',
      style='border: 0px'
    )
      b-icon#searchIcon(icon='search', alt='Search')

    b-button.mx-1(
      @click='toggleSidebar',
      squared,
      style='border: 0px; padding-top: 4px; padding-botton: 4px; padding-right: 10px; padding-left: 10px',
      title='Categories'
    )
      span.navbar-toggler-icon

  .p-1.px-2.mt-2.text-center(v-if='subtitle')
    strong Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.

  b-container
    .row
      LazyHydrate(when-visible)
        b-sidebar#sidebarMenu(
          v-model='sidebar_visible',
          no-slide,
          title='Categories'
        )
          ul.flex-column
            li.mr-2.nav-item(
              v-for='category in this.categories',
              :key='category.id',
              @click='hideSidebar'
            )
              NuxtLink(:to='`/category/${category.slug}`')
                | {{ category.name }}&nbsp
              small
                | ({{ category.use_count }} videos)

      main.col-md-12.col-lg-12.ml-sm-auto.px-md-4.pt-4(role='main')
        nuxt

  footer.text-muted.text-center
    .my-3
      p For more resources visit:
        a(href='https://isha.sadhguru.org/global/en/wisdom')
          |
          | https://isha.sadhguru.org/global/en/wisdom
</template>

<script>
import { BIcon, BIconSearch, BIconShuffle } from 'bootstrap-vue'
import { handleAxiosError, getConfigForRequest } from "~/utils/utils.client"
import LazyHydrate from 'vue-lazy-hydration';
export default {
  scrollToTop: true,
  components: {
    BIcon,
    BIconSearch,
    BIconShuffle,
    LazyHydrate
  },
  data () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    return {
      search_input: "",
      sidebar_visible: false,
      categories: [],

      title: config.title,
      subtitle: config.subtitle,
    }
  },
  methods: {
    async randomVideo () {
      try {
        var url = "/random-video"
        let video = await this.$axios.$get(url)

        this.$router.push("/video/" + video.slug)
      } catch (exception) {
        console.log(exception)
        handleAxiosError(exception, this.$nuxt.context.error)
      }
    },
    toggleSidebar () {

      this.sidebar_visible = !this.sidebar_visible
    },
    hideSidebar (event) {
      this.sidebar_visible = false
    },
    search () {
      this.$router.push(
        {
          path: "/search",
          query: {
            q: this.search_input
          }
        }
      )
    },
  },
  async fetch () {
    const config = getConfigForRequest(this.$nuxt.context.req)
    this.title = config.title
    try {
      this.categories = await this.$axios.$get(
        '/categories/?ordering=name'
      )
    } catch (exception) {
      handleAxiosError(exception, this.$nuxt.context.error)
    }
  },
}
</script>

<style>
/* GLOBAL STYLES
-------------------------------------------------- */
/* Padding below the footer and lighter body text */

.bd-placeholder-img {
  font-size: 1.125rem;
  text-anchor: middle;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

@media (min-width: 768px) {
  .bd-placeholder-img-lg {
    font-size: 3.5rem;
  }
}
</style>

<style scoped>
.collapsing {
  -webkit-transition: none;
  transition: none;
  display: none;
}
</style>
