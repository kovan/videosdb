<template lang="pug">
  div
    #myCarousel.carousel.slide(data-ride="carousel")
      ol.carousel-indicators
        li.active(data-target="#myCarousel" data-slide-to="0")
        li(data-target="#myCarousel" data-slide-to="1")
        li(data-target="#myCarousel" data-slide-to="2")
      .carousel-inner
        .carousel-item.active
          svg.bd-placeholder-img(width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=" :  " preserveaspectratio="xMidYMid slice" focusable="false")
            title  
            rect(width="100%" height="100%" fill="#777")
            text(x="50%" y="50%" fill="#777" dy=".3em")  
          .container
            .carousel-caption.text-left
              h1 Example headline.
              p Some representative placeholder content for the first slide of the carousel.
              p
                a.btn.btn-lg.btn-primary(href="#") Sign up today
        .carousel-item
          svg.bd-placeholder-img(width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=" :  " preserveaspectratio="xMidYMid slice" focusable="false")
            title  
            rect(width="100%" height="100%" fill="#777")
            text(x="50%" y="50%" fill="#777" dy=".3em")  
          .container
            .carousel-caption
              h1 Another example headline.
              p Some representative placeholder content for the second slide of the carousel.
              p
                a.btn.btn-lg.btn-primary(href="#") Learn more
        .carousel-item
          svg.bd-placeholder-img(width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=" :  " preserveaspectratio="xMidYMid slice" focusable="false")
            title  
            rect(width="100%" height="100%" fill="#777")
            text(x="50%" y="50%" fill="#777" dy=".3em")  
          .container
            .carousel-caption.text-right
              h1 One more for good measure.
              p Some representative placeholder content for the third slide of this carousel.
              p
                a.btn.btn-lg.btn-primary(href="#") Browse gallery
      a.carousel-control-prev(href="#myCarousel" role="button" data-slide="prev")
        span.carousel-control-prev-icon(aria-hidden="true")
        span.sr-only Previous
      a.carousel-control-next(href="#myCarousel" role="button" data-slide="next")
        span.carousel-control-next-icon(aria-hidden="true")
        span.sr-only Next

    .album.py-5.bg-light
      .container
        .row
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins
          .col-md-4
            .card.mb-4.shadow-sm
              svg.bd-placeholder-img.card-img-top(width="100%" height="225" xmlns="http://www.w3.org/2000/svg" preserveaspectratio="xMidYMid slice" focusable="false" role="img" aria-label="Placeholder: Thumbnail")
                title Placeholder
                rect(width="100%" height="100%" fill="#55595c")
                text(x="50%" y="50%" fill="#eceeef" dy=".3em") Thumbnail
              .card-body
                p.card-text
                  | This is a wider card with supporting text below as a natural lead-in to additional content. This content is a little bit longer.
                .d-flex.justify-content-between.align-items-center
                  .btn-group
                    button.btn.btn-sm.btn-outline-secondary(type="button") View
                    button.btn.btn-sm.btn-outline-secondary(type="button") Edit
                  small.text-muted 9 mins


</template>

<script >
export default {
  data: () => {
    return {
      page_count: 0,
      current_page: 1,
      videos: [],
      period_options: [
        "this week",
        "this month",
        "this year",
        "always"
      ],
      period: "always",
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
        }
      ]
    }
  },
  props: {
    search: "",

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
  
  updated () {
    this.$fetch()
  },
  methods: {

    handlePageChange () {
      this.$router.push({
        path: this.$route.path,
        query: {
          page: this.current_page
        }
      })
    },
    handleSearch() {
      this.$fetch()
    },
    handleOrderingChange (args) {
      this.ordering = args
      this.$fetch()
    },
    handlePeriodChange (args) {
      this.period = args
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