<template lang="pug">
div

  nav.navbar.navbar-dark.sticky-top.bg-dark.p-0.shadow.flex-md-nowrap.ml-auto
    NuxtLink.navbar-brand.col-md-3.col-lg-2.mr-0.px-3(to="/") Sadhguru wisdom
    b-input.form-control.form-control-dark.w-100(type="search" placeholder="Search" v-model="search_input" @keyup.enter="search")
    b-button.position-absolute.d-md-none.navbar-toggler(@click="sidebar_visible = !sidebar_visible" debounce="500")
      span.navbar-toggler-icon
        



    //- // Right aligned nav items
    //- b-navbar-nav.ml-auto
    //-   b-nav-form
    //-     b-form-input.mr-sm-2(size="sm" placeholder="Search")
    //-     b-button.my-2.my-sm-0(size="sm" type="submit") Search



  .container-fluid
    .row
      b-collapse#sidebarMenu.col-md-3.col-lg-3.d-md-block.bg-light.sidebar.collapse(v-model="sidebar_visible")
        nav
          .sidebar-sticky.pt-3
            h3.sidebar-heading.d-flex.justify-content-between.align-items-center.px-3.mt-4.mb-1.text-muted
              span Categories
            ul.flex-column
              li.nav-item(v-for='category in this.categories'  :key='category.id' @click="categoryClick")
                NuxtLink(:to='`/category/${category.slug}`' )
                  | {{category.name}}

      main(role="main" class="col-md-9 col-lg-9 ml-sm-auto px-md-4 pt-4")
       nuxt


  footer.text-muted.text-center
    div
      p
        small This page is not affiliated or associated to the 
          a(href="http://isha.sadhguru.org​") official Sadhguru website.
      p 
        small 
          | All content is original to 
          a(href="https://www.youtube.com/user/sadhguru") Sadhguru YouTube channel
      p
        small(v-if="this.version")
          | version: {{this.version}} 

    

</template>

<script>

export default {
  data() {
    return {
      search_input: "",
      sidebar_visible: false,
      categories: [],

      title: this.$root.$options.head.title,
      description: this.$root.$options.head.meta[2].content,
    }
  },
  computed: {
    version() {
      return process.env.NUXT_ENV_CURRENT_GIT_SHA;
    },
  },
  methods: {
    categoryClick(event) {
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

.navbar .navbar-toggler {

  right: 1rem;
}

</style>
