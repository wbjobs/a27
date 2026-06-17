<template>
  <div class="page-container p-md">
    <h2 class="page-title">SHAP 分析</h2>
    <el-card class="mt-md">
      <template #header>
        <span>因子可解释性分析</span>
      </template>
      <div class="text-muted">
        该页面用于展示 SHAP 值分析，解释因子模型的预测结果。
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
