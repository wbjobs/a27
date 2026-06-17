<template>
  <div class="page-container p-md">
    <h2 class="page-title">模板市场</h2>
    <el-card class="mt-md">
      <template #header>
        <span>工作流模板</span>
      </template>
      <div class="text-muted">
        该页面展示预设的因子挖掘工作流模板，用户可以快速导入使用。
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
