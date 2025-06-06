<template>
  <div>
    <!-- 这里可以放一些全局的导航栏或其他公共元素 -->
    <!-- 但对于这个简单的例子，我们只显示路由视图 -->
    <router-view />
  </div>
</template>

<script setup>
// 可以在这里导入全局样式或做一些初始化操作
</script>

<style>
/* 全局样式 */
body {
  font-family: sans-serif;
  margin: 0;
  padding: 0;
  background-color: #f8f8f8;
}
</style>
