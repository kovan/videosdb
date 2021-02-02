<template lang="pug">
div

  b-nav.navbar.navbar-dark.sticky-top.bg-dark.p-1.px-2.d-flex

    NuxtLink.mr-auto.navbar-brand(to="/") {{title}}

    NuxtLink(to="/search")
      b-button(variant="light" squared @click="hideSidebar")
        b-icon#searchIcon(icon="search"  alt="Search")    
    // b-input.form-control.form-control-dark(type="search" placeholder="Search" v-model="search_input" @keyup.enter="search")
    b-button(@click="toggleSidebar" variant="light" squared)
      span.navbar-toggler-icon

  div.bg-dark.p-1.px-2(v-if="subtitle")
    h5.text-center {{subtitle}}

  .container-fluid
    .row
      //  b-collapse.col-md-3.col-lg-3.d-md-block.bg-light.sidebar.collapse(v-model="sidebar_visible" position-absolute)
      b-sidebar#sidebarMenu(v-model="sidebar_visible" backdrop shadow)
          h3.sidebar-heading.d-flex.justify-content-between.align-items-center.px-3.mt-4.mb-1.text-muted
            span Categories
          ul.flex-column
            li.nav-item(v-for='category in this.categories'  :key='category.id' @click="hideSidebar")
              NuxtLink(:to='`/category/${category.slug}`' )
                | {{category.name}}

      main(role="main" class="col-md-12 col-lg-12 ml-sm-auto px-md-4 pt-4")
       nuxt


  footer.text-muted.text-center
    div
        small(v-if="this.version")
          | version: {{this.version}} 

    

</template>

<script>
import {BIcon, BIconSearch} from 'bootstrap-vue'

export default {
  scrollToTop: true,
  components: {
    BIcon,
    BIconSearch
  },
  data() {
    return {
      search_input: "",
      sidebar_visible: false,
      categories: [],

      title: this.$config.title,
      subtitle: this.$config.subtitle,
    }
  },
  computed: {
    version() {
      return process.env.VIDEOSDB_CURRENT_GIT_SHA;
    },
  },
  methods: {
    toggleSidebar() {
      this.sidebar_visible = !this.sidebar_visible
    },
    hideSidebar(event) {
      this.sidebar_visible = false
    },
    search() {
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
  async fetch() {
    try {
      this.categories = await this.$axios.$get(
        '/api/categories/?ordering=-use_count'
      )
    } catch (error) {
      console.error(error)
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
