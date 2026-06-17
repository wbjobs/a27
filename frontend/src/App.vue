<template>
  <div class="app-wrapper flex flex-col" style="height: 100vh;">
    <div class="app-nav" style="background: #fff; border-bottom: 1px solid var(--border-color);">
      <el-tabs
        v-model="activeTab"
        class="main-tabs"
        @tab-change="handleTabChange"
      >
        <el-tab-pane label="工作台" name="/" />
        <el-tab-pane label="投资组合" name="/portfolio" />
        <el-tab-pane label="SHAP分析" name="/shap" />
        <el-tab-pane label="模板市场" name="/templates" />
        <el-tab-pane label="实时监控" name="/realtime" />
      </el-tabs>
    </div>
    <div class="app-content flex-1" style="overflow: hidden;">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const activeTab = ref(route.path)

watch(() => route.path, (newPath) => {
  activeTab.value = newPath
})

function handleTabChange(tabName) {
  router.push(tabName)
}
</script>

<style scoped>
.app-wrapper {
  min-width: 0;
}
.main-tabs {
  margin: 0 16px;
}
.main-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}
.main-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.main-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  height: 48px;
  line-height: 48px;
}
</style>
