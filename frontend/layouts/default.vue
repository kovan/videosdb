<template lang="pug">
div
  header
    #navbarHeader.collapse.bg-dark
      .container
        .row
          .col-sm-8.col-md-7.py-4
            h4.text-white About
            p.text-muted
              | Add some information about the album below, the author, or any other background context. Make it a few sentences long so folks can pick up some informative tidbits. Then, link them off to some social networking sites or contact information.
          .col-sm-4.offset-md-1.py-4
            h4.text-white Contact
            ul.list-unstyled
              li
                a.text-white(href="#") Follow on Twitter
              li
                a.text-white(href="#") Like on Facebook
              li
                a.text-white(href="#") Email me
    .navbar.navbar-dark.bg-dark.shadow-sm
      .container.d-flex.justify-content-between
        a.navbar-brand.d-flex.align-items-center(href="#")
          svg.mr-2(xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" aria-hidden="true" viewbox="0 0 24 24" focusable="false")
            path(d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z")
            circle(cx="12" cy="13" r="4")
          strong Album
        button.navbar-toggler(type="button" data-toggle="collapse" data-target="#navbarHeader" aria-controls="navbarHeader" aria-expanded="false" aria-label="Toggle navigation")
          span.navbar-toggler-icon
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

.jumbotron {
  padding-top: 3rem;
  padding-bottom: 3rem;
  margin-bottom: 0;
  background-color: #fff;
}
@media (min-width: 768px) {
  .jumbotron {
    padding-top: 6rem;
    padding-bottom: 6rem;
  }
}

.jumbotron p:last-child {
  margin-bottom: 0;
}

.jumbotron h1 {
  font-weight: 300;
}

.jumbotron .container {
  max-width: 40rem;
}

footer {
  padding-top: 3rem;
  padding-bottom: 3rem;
}

footer p {
  margin-bottom: .25rem;
}


</style>