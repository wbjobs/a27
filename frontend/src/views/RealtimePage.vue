<template>
  <div class="page-container p-md">
    <h2 class="page-title">实时监控</h2>
    <el-card class="mt-md">
      <template #header>
        <span>实时行情与因子监控</span>
      </template>
      <div class="text-muted">
        该页面用于实时监控市场行情和因子表现。
      </div>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.page-container {
  height: 100%;
  overflow: auto;
}
.page-title {
  margin: 0 0 16px 0;
  font-size: 20px;
  font-weight: 600;
}
</style>
