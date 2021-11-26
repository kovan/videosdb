<template lang="pug">
div
  b-nav.navbar.navbar-dark.bg-dark.p-2.pl-3.d-flex.align-middle.justify-content-end
    NuxtLink.mr-auto.h5.mt-1.text-white.align-middle(to='/') {{ this.$config.title }}&nbsp

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

  .p-1.px-2.mt-2.text-center
    strong {{ this.$config.subtitle }}
    br
    small.align-middle Last updated: {{ format(last_updated) }}
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
        nuxt (keep-alive)

  footer.text-muted.text-center
    .my-3
      p For more resources visit:
        a(href='https://isha.sadhguru.org/global/en/wisdom')
          |
          | https://isha.sadhguru.org/global/en/wisdom
      p 
        small This page is not associated with Sadhguru or Isha Foundation in any way.
</template>

<script>
import { collection, query, orderBy } from 'firebase/firestore/lite'
import { format, parseISO } from 'date-fns'
import { BIcon, BIconSearch, BIconShuffle } from 'bootstrap-vue'
import LazyHydrate from 'vue-lazy-hydration'
import { formatDate, getWithCache } from '~/utils/utils'

function getRandomInt(max) {
  return Math.floor(Math.random() * max)
}
export default {
  fetchKey: 'site-sidebar',
  scrollToTop: true,
  components: {
    BIcon,
    BIconSearch,
    BIconShuffle,
    LazyHydrate,
  },
  data() {
    return {
      search_input: '',
      sidebar_visible: false,
      categories: [],

      title: this.$config.title,
      subtitle: this.$config.subtitle,
      last_updated: null,
    }
  },

  methods: {
    format(iso_date) {
      return parseISO(iso_date).toLocaleDateString()
    },
    async randomVideo() {
      const meta_doc = await getWithCache(
        collection(this.$db, 'meta').doc('meta')
      )
      const video_ids = meta_doc.data().videoIds

      let video_id = video_ids[Math.floor(Math.random() * video_ids.length)]
      const video_doc = await getWithCache(
        collection(this.$db, 'videos').doc(video_id)
      )
      let video = video_doc.data()

      this.$router.push('/video/' + video.videosdb.slug)
    },
    toggleSidebar() {
      this.sidebar_visible = !this.sidebar_visible
    },
    hideSidebar(event) {
      this.sidebar_visible = false
    },
    search() {
      this.$router.push({
        path: '/search',
        query: {
          q: this.search_input,
        },
      })
    },
  },
  async fetch() {
    try {
      const q = query(
        collection(this.$db, 'playlists'),
        orderBy('videosdb.lastUpdated', 'desc')
      )

      const meta_q = collection(this.$db, 'meta').doc('meta')

      let [results, meta_results] = await Promise.all([
        getWithCache(q),
        getWithCache(meta_q),
      ])

      results.forEach((doc) => {
        let category = {
          name: doc.data().snippet.title,
          slug: doc.data().videosdb.slug,
          use_count: doc.data().videosdb.videoCount,
        }
        this.categories.push(category)
      })

      this.last_updated = meta_results.data().lastUpdated
    } catch (e) {
      console.trace(e)
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
