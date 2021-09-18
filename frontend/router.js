import Vue from 'vue'
import Router from 'vue-router'

import Home from '~/components/Home.vue'
import Explorer from '~/components/Explorer.vue'
import Category from '~/components/Category.vue'
import Tag from '~/components/Tag.vue'
import Search from '~/components/Search.vue'
import Video from '~/components/Video.vue'


Vue.use(Router)

export function createRouter() {
  return new Router({
    mode: 'history',
    routes: [
      {
          path: '/search',
          component: Search
      },
      {
          path: '/category/:slug/:page?',
          component: Category
      },
      {
          path: '/tag/:slug/:page?',
          component: Tag
      },
      {
          path: '/video/:slug',
          component: Video
      },
      {
        path: '/:page?',
        component: Home
      }
    ]
  })
}