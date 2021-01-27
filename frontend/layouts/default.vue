<template lang="pug">
div
  header
    nav.navbar.navbar-expand-md.navbar-dark.bg-dark.fixed-top
      a.navbar-brand(href="#") Navbar
      button.navbar-toggler(type="button" data-toggle="collapse" data-target="#navbarsExampleDefault" aria-controls="navbarsExampleDefault" aria-expanded="false" aria-label="Toggle navigation")
        span.navbar-toggler-icon
      #navbarsExampleDefault.collapse.navbar-collapse
        ul.navbar-nav.mr-auto
          li.nav-item.active
            a.nav-link(href="#")
              | Home 
              span.sr-only (current)
          li.nav-item
            a.nav-link(href="#") Link
          li.nav-item
            a.nav-link.disabled(href="#" tabindex="-1" aria-disabled="true") Disabled
          li.nav-item.dropdown
            a#dropdown01.nav-link.dropdown-toggle(href="#" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false") Dropdown
            .dropdown-menu(aria-labelledby="dropdown01")
              a.dropdown-item(href="#") Action
              a.dropdown-item(href="#") Another action
              a.dropdown-item(href="#") Something else here
        form.form-inline.my-2.my-lg-0
          input.form-control.mr-sm-2(type="text" placeholder="Search" aria-label="Search")
          button.btn.btn-secondary.my-2.my-sm-0(type="submit") Search


  main(role="main")
    nuxt


  footer.text-muted
    .container
      p.float-right
        a(href="#") Back to top
      p Album example is © Bootstrap, but please download and customize it for yourself!
      p
        | New to Bootstrap? 
        a(href="https://getbootstrap.com/") Visit the homepage
        |  or read our 
        a(href="../getting-started/introduction/") getting started guide
        | .

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

body {
  padding-top: 3rem;
  padding-bottom: 3rem;
  color: #5a5a5a;
}


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






</style>