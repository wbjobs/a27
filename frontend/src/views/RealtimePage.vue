<template>
  <div class="page-container">
    <div class="page-header p-md">
      <h2 class="page-title">实时监控</h2>
    </div>

    <div class="page-content" v-if="hasWorkflow && hasOutputNode && hasDataset">
      <RealtimePanel ref="realtimePanelRef" :workflow="workflow" />
    </div>

    <div class="empty-state p-md" v-else>
      <el-empty description="无法开始实时监控">
        <div class="empty-details">
          <div class="empty-item" v-if="!hasWorkflow">
            <el-icon :size="20" color="#f56c6c"><Warning /></el-icon>
            <span>暂无工作流</span>
          </div>
          <div class="empty-item" v-else-if="!hasOutputNode">
            <el-icon :size="20" color="#e6a23c"><Warning /></el-icon>
            <span>请先设置输出节点</span>
          </div>
          <div class="empty-item" v-if="!hasDataset">
            <el-icon :size="20" color="#f56c6c"><Warning /></el-icon>
            <span>暂无可用数据集</span>
          </div>
        </div>

        <div class="empty-actions mt-lg">
          <el-button type="primary" @click="goToWorkbench">
            <el-icon><SetUp /></el-icon>
            前往工作台
          </el-button>
          <el-button @click="goToTemplates" v-if="!hasWorkflow">
            <el-icon><Collection /></el-icon>
            浏览模板市场
          </el-button>
        </div>

        <el-card class="instruction-card mt-lg">
          <template #header>
            <span class="instruction-title">使用说明</span>
          </template>
          <el-steps :active="0" direction="vertical" finish-status="text">
            <el-step title="构建工作流">
              <template #description>
                前往工作台，添加算子节点并连接工作流
              </template>
            </el-step>
            <el-step title="设置输出节点">
              <template #description>
                右键点击最终输出节点，选择"设为输出节点"
              </template>
            </el-step>
            <el-step title="导入数据集">
              <template #description>
                在工作台左侧面板导入或生成行情数据集
              </template>
            </el-step>
            <el-step title="开始实时监控">
              <template #description>
                选择数据集和推送间隔，点击开始按钮
              </template>
            </el-step>
          </el-steps>
        </el-card>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Warning, SetUp, Collection } from '@element-plus/icons-vue'
import RealtimePanel from '../components/RealtimePanel.vue'
import { useWorkflowStore } from '../stores/workflow'

const router = useRouter()
const workflowStore = useWorkflowStore()
const realtimePanelRef = ref(null)

const workflow = computed(() => workflowStore.exportWorkflow())

const hasWorkflow = computed(() => {
  return workflowStore.nodes && workflowStore.nodes.length > 0
})

const hasOutputNode = computed(() => {
  return workflowStore.outputNodeId !== null
})

const hasDataset = computed(() => {
  return workflowStore.datasets && workflowStore.datasets.length > 0
})

function goToWorkbench() {
  router.push('/workbench')
}

function goToTemplates() {
  router.push('/templates')
}
</script>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.page-header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-content {
  flex: 1;
  min-height: 0;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-details {
  margin: 16px 0;
}

.empty-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  margin: 8px 0;
}

.empty-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.instruction-card {
  max-width: 500px;
  margin: 24px auto 0;
  text-align: left;
}

.instruction-title {
  font-weight: 600;
}

.mt-lg {
  margin-top: 24px;
}

:deep(.el-steps--vertical) {
  padding: 10px 0;
}

:deep(.el-step__title) {
  font-size: 14px;
  font-weight: 500;
}

:deep(.el-step__description) {
  font-size: 13px;
  color: #909399;
}
</style>
