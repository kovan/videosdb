<template lang="pug">
div
  b-nav.navbar.navbar-dark.sticky-top.bg-dark.p-2.px-2.d-flex
    NuxtLink.mr-auto.h4.text-white(to='/') {{ title }}

    b-button.mx-1(squared, href='/video', title='Random video')
      b-icon(icon='shuffle', alt='Random video')

    b-button.mx-1(squared, @click='hideSidebar', to='/search', title='Search')
      b-icon#searchIcon(icon='search', alt='Search')

    b-button.mx-1(
      @click='toggleSidebar',
      squared,
      style='border: 1px',
      title='Categories'
    )
      span.navbar-toggler-icon

  .p-1.px-2.bg-dark(v-if='subtitle')
    h6.text-white.text-center {{ subtitle }}

  .container-fluid
    .row
      b-sidebar#sidebarMenu(v-model='sidebar_visible', backdrop, shadow)
        h3.sidebar-heading.d-flex.justify-content-between.align-items-center.px-3.mt-4.mb-1.text-muted
          span Categories
        ul.flex-column
          li.nav-item(
            v-for='category in this.categories',
            :key='category.id',
            @click='hideSidebar'
          )
            NuxtLink(:to='`/category/${category.slug}`')
              | {{ category.name }}

      main.col-md-12.col-lg-12.ml-sm-auto.px-md-4.pt-4(role='main')
        nuxt

  footer.text-muted.text-center
    div
      p
        hr
        small(v-if='this.version')
          | version: {{ this.version }}
</template>

<script>
import { BIcon, BIconSearch, BIconShuffle } from 'bootstrap-vue'

export default {
  scrollToTop: true,
  components: {
    BIcon,
    BIconSearch,
    BIconShuffle
  },
  data () {
    return {
      search_input: "",
      sidebar_visible: false,
      categories: [],

      title: this.$config.title,
      subtitle: this.$config.subtitle,
    }
  },
  computed: {
    version () {
      return process.env.VIDEOSDB_CURRENT_GIT_SHA;
    },
  },
  methods: {
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
    try {
      this.categories = await this.$axios.$get(
        '/api/categories/?ordering=-use_count'
      )
    } catch (error) {
      console.exception(error)
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
