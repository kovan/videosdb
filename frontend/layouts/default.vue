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
    b-container
        .row
            LazyHydrate(when-visible)
                b-sidebar#sidebarMenu(
                    v-model='sidebar_visible',
                    no-slide,
                    title='Categories'
                )
                    b-container
                    .col
                        small Order by:
                    .col
                        b-form-select(
                            text='Order by',
                            v-model='ordering',
                            :options='ordering_options',
                            @change='handleChange'
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
                nuxt

    footer.text-muted.text-center
        .my-3
            p For more resources visit:
                a(:href="$config.website")
                    | {{ $config.website }}
</template>

<script>
function getRandomInt(max) {
    return Math.floor(Math.random() * max)
}
import {
    getDoc,
    doc,
} from 'firebase/firestore/lite'

import { parseISO } from 'date-fns'
import { BIcon, BIconSearch, BIconShuffle } from 'bootstrap-vue'
import { getVuexData } from '~/utils/utils'
import LazyHydrate from 'vue-lazy-hydration'
import { orderBy as lodashOrderBy } from 'lodash'



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
            video_count: 0,
            ordering_options: [
                {
                    text: 'Last updated',
                    value: 'last_updated',
                },
                {
                    text: 'Video count',
                    value: 'use_count',
                },
                {
                    text: 'Alphabetical',
                    value: 'name',
                },
            ],
            ordering: 'last_updated',
        }
    },

    methods: {
        async handleChange() {
            let directions = {
                name: 'asc',
                use_count: 'desc',
                last_updated: 'desc',
            }
            this.categories = lodashOrderBy(
                this.categories,
                [this.ordering],
                [directions[this.ordering]]
            )
        },
        format(iso_date) {
            return parseISO(iso_date).toLocaleDateString()
        },
        async randomVideo() {

            const video_ids_doc = await getDoc(doc(this.$db, "meta/video_ids"))
            const video_ids = video_ids_doc.data().videoIds

            let video_id = video_ids[Math.floor(Math.random() * video_ids.length)]
            const video_doc = await getDoc(doc(this.$db, "videos/" + video_id))

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
            if (
                typeof this.$store.state.categories == 'undefined'
            ) {
                let vuex_data = await getVuexData(this.$db)
                this.$store.commit('setInitial', vuex_data)
            }

            this.categories = [...this.$store.state.categories]
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
</style>
