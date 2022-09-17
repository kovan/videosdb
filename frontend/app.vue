<template lang="pug">
div
    b-nav.navbar.navbar-dark.bg-dark.p-2.pl-3.d-flex.align-middle.justify-content-end
        NuxtLink.mr-auto.h5.mt-1.text-white.align-middle(to='/') {{ config.public.title }}&nbsp

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
        strong {{ config.public.subtitle }}
        br
        small.align-middle  {{ this.$store.state.meta_data.videoIds.length }} videos in the database. Last updated: {{ format(last_updated) }}
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
                a(:href="config.public.website")
                    | {{ config.public.website }}
</template>

<script>

function getRandomInt(max) {
    return Math.floor(Math.random() * max)
}
import { parseISO } from 'date-fns'
import { getVuexData } from '~/utils/utils'
import LazyHydrate from 'vue-lazy-hydration'
import { orderBy } from 'lodash-es'


export default {
    fetchKey: 'site-sidebar',
    scrollToTop: true,
    data() {
        return {
            search_input: '',
            sidebar_visible: false,
            categories: [],

            title: config.public.title,
            subtitle: config.public.subtitle,
            last_updated: null,
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
            this.categories = orderBy(
                this.categories,
                [this.ordering],
                [directions[this.ordering]]
            )
        },
        format(iso_date) {
            return parseISO(iso_date).toLocaleDateString()
        },
        async randomVideo() {
            const video_ids = this.$store.state.meta_data.videoIds

            let video_id = video_ids[Math.floor(Math.random() * video_ids.length)]
            const video_doc = await this.$db.collection('videos').doc(video_id).get()

            let video = video_doc.data()

            await navigateTo(('/video/' + video.videosdb.slug))
        },
        toggleSidebar() {
            this.sidebar_visible = !this.sidebar_visible
        },
        hideSidebar(event) {
            this.sidebar_visible = false
        },
        async search() {
            await navigateTo({
                path: '/search',
                query: {
                    q: this.search_input,
                },
            })
        },
    },
    async fetch() {
        if (
            typeof this.$store.state.categories == 'undefined' ||
            typeof this.$store.state.meta_data.lastUpdated == 'undefined'
        ) {
            let vuex_data = await getVuexData(this.$db)
            this.$store.commit('setInitial', vuex_data)
        }

        this.categories = [...this.$store.state.categories]
        this.last_updated = this.$store.state.meta_data.lastUpdated
    },
}
</script>

<script setup>
const config = useRuntimeConfig()
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
