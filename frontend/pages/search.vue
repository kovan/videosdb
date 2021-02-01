<template lang="pug">
div
  client-only
    div.gcse-search
</template>

<script>

export default {
  head () {
    return {
      title: "Search",
      meta: [
        {
          hid: 'description',
          name: 'description',
          content: "Search"
        }
      ],
      script: [ {
          src: "https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635",
          async: false,
          head:true
        }
      ]
    }
  }
}
</script>

<style>

</style>