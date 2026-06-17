<template>
  <div class="app-container flex flex-col" style="height: 100vh;">
    <div class="app-header flex items-center justify-between p-sm" style="background: #fff; border-bottom: 1px solid var(--border-color);">
      <div class="flex items-center gap-md">
        <div class="flex items-center gap-sm">
          <el-icon :size="24" color="#409eff"><DataLine /></el-icon>
          <h1 style="font-size: 18px; font-weight: 600; margin: 0;">股票因子挖掘工作台</h1>
        </div>
        <el-tag size="small" type="info">DuckDB + Observable</el-tag>
      </div>
      
      <div class="flex items-center gap-sm">
        <el-select
          v-model="selectedDataset"
          placeholder="选择数据集"
          style="width: 220px;"
          size="default"
          @change="handleDatasetChange"
        >
          <el-option
            v-for="ds in workflowStore.datasets"
            :key="ds.name"
            :label="`${ds.name} (${ds.row_count}行)`"
            :value="ds.name"
          />
        </el-select>
        <el-button type="primary" :icon="MagicStick" @click="showSampleDialog = true">生成示例数据</el-button>
        <el-upload
          :show-file-list="false"
          :before-upload="handleFileUpload"
          accept=".csv,.parquet"
        >
          <el-button :icon="Upload">导入数据</el-button>
        </el-upload>
        <el-divider direction="vertical" />
        <el-button :icon="Delete" @click="clearWorkflow">清空</el-button>
        <el-button type="success" :icon="Play" :loading="isComputing" @click="computeFactor">计算因子</el-button>
        <el-button type="warning" :icon="Histogram" :loading="isBacktesting" @click="runBacktest" :disabled="!workflowStore.factorResult">一键回测</el-button>
        <el-button :icon="Share" @click="shareWorkflow">分享</el-button>
      </div>
    </div>

    <div class="flex flex-1" style="overflow: hidden;">
      <div style="width: 240px; background: #fff; border-right: 1px solid var(--border-color); overflow-y: auto;" class="p-sm">
        <OperatorPalette />
      </div>

      <div class="flex flex-col flex-1" style="overflow: hidden;">
        <WorkflowCanvas />
      </div>

      <div style="width: 340px; background: #fff; border-left: 1px solid var(--border-color); overflow-y: auto;" class="p-sm">
        <div v-if="workflowStore.selectedNodeId">
          <NodePropertyPanel />
        </div>
        <div v-else-if="workflowStore.backtestResult">
          <BacktestPanel @view-details="openResultViewer" />
        </div>
        <div v-else-if="workflowStore.factorResult">
          <FactorResultPanel />
        </div>
        <div v-else>
          <div class="section-title">提示</div>
          <div class="text-muted">
            <p>• 从左侧面板拖拽算子到画布</p>
            <p>• 连接节点输入输出端口构建工作流</p>
            <p>• 点击节点可调整参数</p>
            <p>• 选择数据集后点击「计算因子」</p>
            <p>• 点击节点头部的★设为输出节点</p>
          </div>
          <div class="section-title mt-md">前向验证</div>
          <el-switch v-model="forwardValidation" active-text="严格模式" inactive-text="普通模式" />
          <div class="text-muted" style="margin-top: 8px; font-size: 11px;">
            开启后每个计算时点只使用该时点之前数据，杜绝未来函数
          </div>
        </div>
      </div>
    </div>

    <ResultViewer ref="resultViewerRef" />

    <el-dialog v-model="showSampleDialog" title="生成示例数据" width="480px">
      <el-form label-position="top">
        <el-form-item label="股票数量 (5-500)">
          <el-slider v-model="sampleParams.nStocks" :min="5" :max="500" show-input />
        </el-form-item>
        <el-form-item label="交易日数量 (20-2520)">
          <el-slider v-model="sampleParams.nDays" :min="20" :max="2520" show-input />
        </el-form-item>
        <el-form-item label="数据集名称（可选）">
          <el-input v-model="sampleParams.name" placeholder="留空自动生成" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSampleDialog = false">取消</el-button>
        <el-button type="primary" :loading="isGenerating" @click="generateSample">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataLine, MagicStick, Upload, Delete, Play, Histogram, Share } from '@element-plus/icons-vue'
import { useWorkflowStore } from './stores/workflow'
import { dataApi, factorApi, backtestApi } from './api'
import OperatorPalette from './components/OperatorPalette.vue'
import WorkflowCanvas from './components/WorkflowCanvas.vue'
import NodePropertyPanel from './components/NodePropertyPanel.vue'
import BacktestPanel from './components/BacktestPanel.vue'
import FactorResultPanel from './components/FactorResultPanel.vue'
import ResultViewer from './components/ResultViewer.vue'

const workflowStore = useWorkflowStore()
const resultViewerRef = ref(null)

const selectedDataset = ref(null)
const showSampleDialog = ref(false)
const isComputing = ref(false)
const isBacktesting = ref(false)
const isGenerating = ref(false)
const sampleParams = ref({
  nStocks: 50,
  nDays: 252,
  name: ''
})
const forwardValidation = ref(false)

const isDatasetSelected = computed(() => !!selectedDataset.value)

onMounted(async () => {
  try {
    const [opRes, dsRes] = await Promise.all([
      factorApi.listOperators(),
      dataApi.listDatasets()
    ])
    workflowStore.setOperators(opRes.operators, opRes.by_category)
    workflowStore.setDatasets(Array.isArray(dsRes) ? dsRes : [])
    
    if (workflowStore.datasets.length > 0) {
      selectedDataset.value = workflowStore.datasets[0].name
      workflowStore.setCurrentDataset(selectedDataset.value)
    }

    workflowStore.loadFromUrl()
  } catch (e) {
    ElMessage.error('初始化失败: ' + e.message)
  }
})

async function handleDatasetChange(val) {
  workflowStore.setCurrentDataset(val)
}

async function handleFileUpload(file) {
  try {
    const ext = file.name.split('.').pop().toLowerCase()
    const res = await dataApi.importData(file, ext, 'daily')
    if (res.success) {
      ElMessage.success(res.message)
      const ds = await dataApi.listDatasets()
      workflowStore.setDatasets(Array.isArray(ds) ? ds : [])
      selectedDataset.value = res.table_name
      workflowStore.setCurrentDataset(res.table_name)
    }
  } catch (e) {
    ElMessage.error('导入失败: ' + e.message)
  }
  return false
}

async function generateSample() {
  isGenerating.value = true
  try {
    const res = await dataApi.generateSample(
      sampleParams.value.nStocks,
      sampleParams.value.nDays,
      sampleParams.value.name || null
    )
    if (res.success) {
      ElMessage.success(res.message)
      const ds = await dataApi.listDatasets()
      workflowStore.setDatasets(Array.isArray(ds) ? ds : [])
      selectedDataset.value = res.table_name
      workflowStore.setCurrentDataset(res.table_name)
      showSampleDialog.value = false
    }
  } catch (e) {
    ElMessage.error('生成失败: ' + e.message)
  } finally {
    isGenerating.value = false
  }
}

function clearWorkflow() {
  ElMessageBox.confirm('确定要清空工作流吗？', '提示', {
    type: 'warning'
  }).then(() => {
    workflowStore.clearWorkflow()
    ElMessage.success('已清空')
  }).catch(() => {})
}

async function computeFactor() {
  if (!isDatasetSelected.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  if (workflowStore.nodes.length === 0) {
    ElMessage.warning('请先构建工作流')
    return
  }
  if (!workflowStore.outputNodeId) {
    ElMessage.warning('请设置输出节点')
    return
  }

  isComputing.value = true
  try {
    const wf = workflowStore.exportWorkflow()
    const res = await factorApi.computeFactor(
      wf,
      selectedDataset.value,
      null, null, null,
      forwardValidation.value
    )
    if (res.success) {
      ElMessage.success(res.message)
      workflowStore.setFactorResult(res.factor_values, res.stats)
      if (res.forward_validation) {
        ElMessage.info(res.forward_validation.message)
      }
      workflowStore.syncToUrl()
    } else {
      ElMessage.error(res.message || '计算失败')
    }
  } catch (e) {
    ElMessage.error('计算失败: ' + e.message)
  } finally {
    isComputing.value = false
  }
}

async function runBacktest() {
  if (!workflowStore.factorResult) {
    ElMessage.warning('请先计算因子')
    return
  }

  isBacktesting.value = true
  try {
    const res = await backtestApi.runBacktest({
      factor_name: workflowStore.workflowName,
      factor_values: workflowStore.factorResult,
      dataset_name: selectedDataset.value,
      n_groups: 5,
      holding_period: 1,
      commission_rate: 0.0003
    })
    if (res.success) {
      ElMessage.success(res.message)
      workflowStore.setBacktestResult(res)
    } else {
      ElMessage.error(res.message || '回测失败')
    }
  } catch (e) {
    ElMessage.error('回测失败: ' + e.message)
  } finally {
    isBacktesting.value = false
  }
}

function openResultViewer() {
  if (resultViewerRef.value && workflowStore.backtestResult?.success) {
    resultViewerRef.value.visible = true
  } else if (!workflowStore.backtestResult) {
    ElMessage.warning('请先运行回测')
  } else if (!workflowStore.backtestResult.success) {
    ElMessage.warning(workflowStore.backtestResult.message || '回测未成功')
  }
}

function shareWorkflow() {
  if (workflowStore.nodes.length === 0) {
    ElMessage.warning('请先构建工作流')
    return
  }
  const url = workflowStore.getShareUrl()
  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('分享链接已复制到剪贴板')
  }).catch(() => {
    ElMessage({ type: 'info', message: url, duration: 10000 })
  })
}
</script>
