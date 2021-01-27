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

<style scoped>


/* GLOBAL STYLES
-------------------------------------------------- */
/* Padding below the footer and lighter body text */

body {
  padding-top: 3rem;
  padding-bottom: 3rem;
  color: #5a5a5a;
}


/* CUSTOMIZE THE CAROUSEL
-------------------------------------------------- */

/* Carousel base class */
/* .carousel {
  margin-bottom: 4rem;
} */
/* Since positioning the image, we need to help out the caption */
.carousel-caption {
  bottom: 3rem;
  z-index: 10;
}

/* Declare heights because of positioning of img element */
.carousel-item {
  height: 32rem;
}
.carousel-item > img {
  position: absolute;
  top: 0;
  left: 0;
  min-width: 100%;
  height: 32rem;
}


/* MARKETING CONTENT
-------------------------------------------------- */

/* Center align the text within the three columns below the carousel */
.marketing .col-lg-4 {
  margin-bottom: 1.5rem;
  text-align: center;
}
.marketing h2 {
  font-weight: 400;
}
.marketing .col-lg-4 p {
  margin-right: .75rem;
  margin-left: .75rem;
}


/* Featurettes
------------------------- */

.featurette-divider {
  margin: 5rem 0; /* Space out the Bootstrap <hr> more */
}

/* Thin out the marketing headings */
.featurette-heading {
  font-weight: 300;
  line-height: 1;
  letter-spacing: -.05rem;
}


/* RESPONSIVE CSS
-------------------------------------------------- */

@media (min-width: 40em) {
  /* Bump up size of carousel content */
  .carousel-caption p {
    margin-bottom: 1.25rem;
    font-size: 1.25rem;
    line-height: 1.4;
  }

  .featurette-heading {
    font-size: 50px;
  }
}

@media (min-width: 62em) {
  .featurette-heading {
    margin-top: 7rem;
  }
}



</style>