<template>
  <div id="main-app-container">
    <router-view />
  </div>
</template>

<script setup>
// No specific script needed for this basic layout
</script>

<style>
html, body, #app, #main-app-container {
  height: 100%;
  margin: 0;
  padding: 0;
  width: 100%;
  overflow-x: hidden; /* Prevent horizontal scroll on body/app */
}
/* Ensure router-view content can also flex if needed by child components */
#main-app-container > * {
  height: 100%;
  width: 100%;
}
</style>