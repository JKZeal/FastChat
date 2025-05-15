<template>
  <div id="main-app-container">
    <router-view />
  </div>
</template>

<script setup>

</script>

<style>
html, body, #app, #main-app-container {
  height: 100%;
  margin: 0;
  padding: 0;
  width: 100%;
  overflow-x: hidden; /* Prevent horizontal scroll on body/app */
}

#main-app-container > * {
  height: 100%;
  width: 100%;
}
</style>