<template lang="pug">
v-app(dark)
  v-navigation-drawer(v-model='drawer' :mini-variant='miniVariant' :clipped='clipped' fixed app)
    v-list
      v-list-item(v-for='(item, i) in items' :key='i' :to='item.to' router exact)
        v-list-item-action
          v-icon {{ item.icon }}
        v-list-item-content
          v-list-item-title(v-text='item.title')
      v-list-group(:value="true" prepend-icon="mdi-account-circle")
        template(v-slot:activator="")
          v-list-item-title Categories
        v-list-item(v-for="category in this.categories" :key="category.id" :to="'/categories/' + category.slug" router exact)
            v-list-item-title(v-text="category.name")


        

  v-app-bar(:clipped-left='clipped' fixed app)
    v-app-bar-nav-icon(@click.stop='drawer = !drawer')
    v-btn(icon @click.stop='miniVariant = !miniVariant')
      v-icon mdi-{{ &grave;chevron-${miniVariant ? &apos;right&apos; : &apos;left&apos;}&grave; }}
    v-btn(icon @click.stop='clipped = !clipped')
      v-icon mdi-application
    v-btn(icon @click.stop='fixed = !fixed')
      v-icon mdi-minus
    v-toolbar-title(v-text='title')
    v-spacer
    v-btn(icon @click.stop='rightDrawer = !rightDrawer')
      v-icon mdi-menu
  v-main
    v-container
      nuxt
  v-navigation-drawer(v-model='rightDrawer' :right='right' temporary fixed)
    v-list
      v-list-item(@click.native='right = !right')
        v-list-item-action
          v-icon(light)
            | mdi-repeat
        v-list-item-title Switch drawer (click me)
  v-footer(:absolute='!fixed' app)
    span &copy; {{ new Date().getFullYear() }}

</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      clipped: false,
      drawer: false,
      fixed: false,
      items: [
        {
          icon: 'mdi-apps',
          title: 'Latest videos',
          to: '/',
        },
        {
          icon: 'mdi-apps',
          title: 'Search videos',
          to: '/search-videos',
        },        
        {
          icon: 'mdi-apps',
          title: 'Random video',
          to: '/random-video',
        },
        {
          icon: 'mdi-apps',
          title: 'Most viewed videos',
          to: '/most-viewed-videos',
        },
        {
          icon: 'mdi-apps',
          title: 'Most liked videos',
          to: '/most-liked-videos',
        },
        {
          icon: 'mdi-apps',
          title: 'Most favorites videos',
          to: '/most-favorited-videos',
        },
        {
          icon: 'mdi-apps',
          title: 'Most commented videos',
          to: '/most-commented-videos',
        },        
      ],
      categories: [],
      miniVariant: false,
      right: true,
      rightDrawer: false,
      title: 'Sadhguru wisdom',
    }
  },
  async fetch() {
    let categories = await axios.get('http://localhost:8000/api/categories/')

    this.categories = categories.data
  },
}
</script>
