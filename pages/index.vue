<template lang="pug">
  v-container
    v-row
      template(v-for='n in 4')
        v-col.mt-2(:key='n' cols='12')
          strong Category {{ n }}
        v-col(v-for='j in 6' :key='`${n}${j}`' cols='6' md='2')
          v-sheet(height='150')



        v-card-actions
          v-spacer
            v-btn(color='primary' nuxt='' to='/inspire')
              | Continue
</template>

<script>
import Logo from '~/components/Logo.vue'
import VuetifyLogo from '~/components/VuetifyLogo.vue'


export default {
  components: {
    Logo,
    VuetifyLogo
  },
  data() {
    return {
      categories : []
    }
  },
  async fetch() { debugger
    this.categories = await this.$http.$get(
       'http://localhost:8000/api/categories/'
     )
     
     
  }
}
</script>
