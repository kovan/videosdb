<template lang="pug">
LazyHydrate(when-visible)
    .card.mb-4.shadow-sm.text-center
        NuxtLink(:to='"/video/" + this.video.videosdb.slug')
        b-img-lazy.bd-placeholder-img.card-img-top(
            :src='this.video.snippet.thumbnails.medium.url',
            height='180',
            width='320',
            :id='this.video.id',
            :alt='this.video.snippet.title',
            fluid
        )
        b-popover(
            :target='this.video.id',
            triggers='hover focus',
            :content='this.video.snippet.description'
        )
        .card-body
        p.card-text
            NuxtLink(:to='"/video/" + this.video.videosdb.slug')
            | {{ this.video.snippet.title }}
        .d-flex.justify-content-between.align-items-center
            small.text-muted Published: <br/>{{ $moment(this.video.snippet.publisheAt).format("MMM Do YYYY") }}
            small.text-muted Duration: <br/>{{ new Date(this.video.videosdb.durationSeconds * 1000).toISOString().substr(11, 8) }}
</template>

script>
import LazyHydrate from 'vue-lazy-hydration'
export default {
    components: {
        LazyHydrate,
    },
    props: {
        video: function () {
            return {}
        },
    },
}
</script>
