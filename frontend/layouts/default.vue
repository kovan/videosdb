<template lang="pug">
div

  nav.navbar.navbar-dark.sticky-top.bg-dark.flex-md-nowrap.p-0.shadow
    NuxtLink.navbar-brand.col-md-3.col-lg-2.mr-0.px-3(to="/") Sadhguru wisdom
    button.navbar-toggler.position-absolute.d-md-none.collapsed(type="button" data-toggle="collapse" data-target="#sidebarMenu" aria-controls="sidebarMenu" aria-expanded="false" aria-label="Toggle navigation")
      span.navbar-toggler-icon
    input.form-control.form-control-dark.w-100(type="text" placeholder="Search" aria-label="Search")



    //- // Right aligned nav items
    //- b-navbar-nav.ml-auto
    //-   b-nav-form
    //-     b-form-input.mr-sm-2(size="sm" placeholder="Search")
    //-     b-button.my-2.my-sm-0(size="sm" type="submit") Search



  .container-fluid
    .row
      nav#sidebarMenu.col-md-3.col-lg-2.d-md-block.bg-light.sidebar.collapse
        .sidebar-sticky.pt-3
          h3.sidebar-heading.d-flex.justify-content-between.align-items-center.px-3.mt-4.mb-1.text-muted
            span Categories
            a.d-flex.align-items-center.text-muted
              span(data-feather="plus-circle")
          ul.nav.flex-column
            li.nav-item(v-for='category in this.categories'  :key='category.id')
              NuxtLink(:to='`/category/${category.slug}`')
                | - {{category.name}}

      main(role="main" class="col-md-9 ml-sm-auto col-lg-10 px-md-4")
       nuxt


  footer.text-muted
    .container
      p This page is not affiliated or asociated to the 
        a(href="http://isha.sadhguru.org​") official Sadhguru website.
      p All content is original to 
        a(href="https://www.youtube.com/user/sadhguru") Sadhguru YouTube channel

    

</template>

<script>
import NavBar from '~/components/NavBar.vue';  

export default {
  data () { 
    return {
      clipped: true,
      drawer: true,
      fixed: false,
      items: [
        // {
        //   icon: 'mdi-fire',
        //   title: 'Latest videos',
        //   to: '/',
        // },
        // {
        //   icon: 'mdi-magnify',
        //   title: 'Search videos',
        //   to: '/search-videos',
        // },
        // {
        //   icon: 'mdi-shuffle',
        //   title: 'Random video',
        //   to: '/random-video',
        // },
        // {
        //   icon: 'mdi-eye',
        //   title: 'Most viewed videos',
        //   to: '/most-viewed',
        // },
        // {
        //   icon: 'mdi-thumb-up',
        //   title: 'Most liked videos',
        //   to: '/most-liked',
        // },
        // {
        //   icon: 'mdi-star',
        //   title: 'Most favorited videos',
        //   to: '/most-favorited',
        // },
        // {
        //   icon: 'mdi-comment',
        //   title: 'Most commented videos',
        //   to: '/most-commented',
        // },
      ],
      categories: [],
      miniVariant: false,
      right: false,
      rightDrawer: false,
      title: this.$root.$options.head.title,
      description: this.$root.$options.head.meta[2].content,
    }
  },
  methods: {
    handleSearch () {

    }
  },
  async fetch () {
    try {
      this.categories = await this.$axios.$get('/api/categories/?ordering=-use_count')  
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

footer {
  margin-top: 50px
}

.feather {
  width: 16px;
  height: 16px;
  vertical-align: text-bottom;
}

/*
 * Sidebar
 */

.sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: 100; /* Behind the navbar */
  padding: 48px 0 0; /* Height of navbar */
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, .1);
}

@media (max-width: 767.98px) {
  .sidebar {
    top: 5rem;
  }
}

.sidebar-sticky {
  position: relative;
  top: 0;
  height: calc(100vh - 48px);
  padding-top: .5rem;
  overflow-x: hidden;
  overflow-y: auto; /* Scrollable contents if viewport is shorter than content. */
}

@supports ((position: -webkit-sticky) or (position: sticky)) {
  .sidebar-sticky {
    position: -webkit-sticky;
    position: sticky;
  }
}

.sidebar .nav-link {
  font-weight: 500;
  color: #333;
}

.sidebar .nav-link .feather {
  margin-right: 4px;
  color: #999;
}

.sidebar .nav-link.active {
  color: #007bff;
}

.sidebar .nav-link:hover .feather,
.sidebar .nav-link.active .feather {
  color: inherit;
}

.sidebar-heading {
  font-size: .75rem;
  text-transform: uppercase;
}

/*
 * Navbar
 */

.navbar-brand {
  padding-top: .75rem;
  padding-bottom: .75rem;
  font-size: 1rem;
  background-color: rgba(0, 0, 0, .25);
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, .25);
}

.navbar .navbar-toggler {
  top: .25rem;
  right: 1rem;
}

.navbar .form-control {
  padding: .75rem 1rem;
  border-width: 0;
  border-radius: 0;
}

.form-control-dark {
  color: #fff;
  background-color: rgba(255, 255, 255, .1);
  border-color: rgba(255, 255, 255, .1);
}

.form-control-dark:focus {
  border-color: transparent;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, .25);
}



</style>