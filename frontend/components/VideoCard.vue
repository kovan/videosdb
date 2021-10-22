<template lang="pug">
LazyHydrate(when-visible)
    .card.mb-4.shadow-sm.text-center
        NuxtLink(:to='"/video/" + video.slug')
        b-img-lazy.bd-placeholder-img.card-img-top(
            :src='video.thumbnails.medium.url',
            height='180',
            width='320',
            :id='video.youtube_id',
            :alt='video.title',
            fluid
        )
        b-popover(
            :target='video.youtube_id',
            triggers='hover focus',
            :content='video.description_trimmed'
        )
        .card-body
        p.card-text
            NuxtLink(:to='"/video/" + video.slug')
            | {{ video.title }}
        .d-flex.justify-content-between.align-items-center
            small.text-muted Published: {{ new Date(video.yt_published_date).toLocaleDateString() }}
            small.text-muted Duration: {{ new Date(video.duration_seconds * 1000).toISOString().substr(11, 8) }}
</template>

// <script>
// export default {
//     props: {
//         video
//     }
// }
// </script>