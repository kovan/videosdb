<!-- <div class="container">
  <Button on:click={() => clicked++}>
    <Icon class="material-icons">thumb_up</Icon>
    <Label>Click Me</Label>
  </Button>
  <p class="mdc-typography--body1">
    {#if clicked}
      You've clicked the button {clicked} time{clicked === 1 ? '' : 's'}.
    {:else}
      <span class="grayed">You haven't clicked the button.</span>
    {/if}
  </p>
</div> -->

<div>
  <List class="demo-list">
    {#each videos as video}
    <Item on:SMUI:action={() => clickedSimple = 'Cut'}><Text>{video.title}</Text></Item>
    {/each}
  </List>
</div>

<pre class="status">Clicked: {clickedSimple}</pre>

<script>
  import List, {Item, Separator,Text} from '@smui/list';
  import axios from "axios";
    // axios.defaults.proxy = {
    //   protocol: "http",
    //   host:"192.168.0.19",
    //   port : 8000
    // }
  let videos = [];

  axios.get('http://192.168.0.19:8000/api/videos/')
  .then(function (response) {
    videos = response.data.results;
    console.log(response);
  })
  .catch(function (error) {
    // handle error
    console.log(error);
  })
  .then(function () {
    // always executed
  });

  //import Button, {Label, Icon} from '@smui/button';

  let clickedSimple = "Nothing yet"
</script>

<style>

</style>