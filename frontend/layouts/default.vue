<template lang="pug">
v-app(dark)
  v-navigation-drawer(
    v-model='drawer',
    :mini-variant='miniVariant',
    clipped=true,
    app,
    mobile-breakpoint=800,
    width=350)
    v-list
      v-list-item(
        v-for='(item, i) in items',
        :key='i',
        :to='item.to',
        router,
        exact,
        nuxt
      )
        v-list-item-action
          v-icon {{ item.icon }}
        v-list-item-content
          v-list-item-title(v-text='item.title')

      v-list-group(:value='true', prepend-icon='mdi-text-short')
        template(v-slot:activator='')
          v-list-item-title 
            | Categories
        v-list-item(
          v-for='category in this.categories',
          :key='category.id',
          :to='`/category/${category.slug}`',
          router,
          nuxt,
          v-text='category.name',
          style='border-bottom: 1px dotted'
        )

  v-app-bar(:clipped-left='clipped', app, collapse-on-scroll, fixed)

    v-app-bar-nav-icon(@click.stop='drawer = !drawer')
    v-spacer
    v-toolbar-title(v-text='title')
    template(v-slot:extension="")
      v-tabs(centered)
        v-tab Latest
        v-tab Most viewed
        v-tab Most liked
        v-tab Most favorited
        v-tab Most commented
    v-spacer

  v-main
    v-container
      nuxt
  
</template>

<script>


export default {
  data () { debugger
    return {
      clipped: true,
      drawer: true,
      fixed: false,
      items: [
        {
          icon: 'mdi-fire',
          title: 'Latest videos',
          to: '/',
        },
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
        {
          icon: 'mdi-eye',
          title: 'Most viewed videos',
          to: '/most-viewed',
        },
        {
          icon: 'mdi-thumb-up',
          title: 'Most liked videos',
          to: '/most-liked',
        },
        {
          icon: 'mdi-star',
          title: 'Most favorited videos',
          to: '/most-favorited',
        },
        {
          icon: 'mdi-comment',
          title: 'Most commented videos',
          to: '/most-commented',
        },
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
