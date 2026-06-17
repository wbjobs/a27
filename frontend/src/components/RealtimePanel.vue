<template>
  <div class="realtime-panel">
    <div class="control-bar">
      <div class="control-left">
        <div class="control-item">
          <span class="control-label">数据集</span>
          <el-select
            v-model="selectedDataset"
            placeholder="选择数据集"
            style="width: 200px;"
            size="default"
            :disabled="isConnected || isConnecting"
          >
            <el-option
              v-for="ds in datasets"
              :key="ds.name"
              :label="`${ds.name} (${ds.row_count}行)`"
              :value="ds.name"
            />
          </el-select>
        </div>

        <div class="control-item">
          <span class="control-label">推送间隔</span>
          <el-slider
            v-model="pushInterval"
            :min="0.5"
            :max="5"
            :step="0.5"
            :disabled="isConnected || isConnecting"
            style="width: 150px;"
            show-input
            input-size="small"
          />
          <span class="interval-unit">秒</span>
        </div>

        <div class="control-item">
          <el-tag :type="connectionStatusType" effect="dark" size="small">
            {{ connectionStatusText }}
          </el-tag>
        </div>
      </div>

      <div class="control-right">
        <el-button
          type="success"
          :icon="VideoPlay"
          @click="handleStart"
          :disabled="!selectedDataset || isConnected || isConnecting"
          :loading="isConnecting"
        >
          开始
        </el-button>
        <el-button
          type="warning"
          :icon="VideoPause"
          @click="handlePause"
          :disabled="!isConnected || isPaused"
        >
          暂停
        </el-button>
        <el-button
          type="danger"
          :icon="VideoStop"
          @click="handleStop"
          :disabled="!isConnected && !isConnecting"
        >
          停止
        </el-button>
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-info">
        <span class="progress-label">播放进度</span>
        <span class="progress-value">{{ currentDate || '-' }}</span>
        <span class="progress-percent">{{ formatPercent(progressPercent) }}</span>
      </div>
      <el-progress
        :percentage="progressPercent"
        :stroke-width="8"
        :show-text="false"
        status="success"
      />
    </div>

    <div class="stats-row">
      <el-card class="stat-card-dark">
        <div class="stat-content">
          <div class="stat-icon date-icon">
            <el-icon :size="28"><Calendar /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value-dark">{{ currentDate || '-' }}</div>
            <div class="stat-label-dark">当前日期</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card-dark">
        <div class="stat-content">
          <div class="stat-icon stock-icon">
            <el-icon :size="28"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value-dark">{{ nStocks }}</div>
            <div class="stat-label-dark">更新股票数</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card-dark">
        <div class="stat-content">
          <div class="stat-icon mean-icon">
            <el-icon :size="28"><DataLine /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value-dark" :class="{ 'text-positive': factorMean > 0, 'text-negative': factorMean < 0 }">
              {{ formatNumber(factorMean, 4) }}
            </div>
            <div class="stat-label-dark">因子均值</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card-dark">
        <div class="stat-content">
          <div class="stat-icon std-icon">
            <el-icon :size="28"><Operation /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value-dark">{{ formatNumber(factorStd, 4) }}</div>
            <div class="stat-label-dark">因子标准差</div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="tables-container">
      <div class="table-panel">
        <div class="panel-header">
          <span class="panel-title">实时 K 线数据</span>
          <el-tag type="info" size="small">
            {{ klineData.length }} 条记录
          </el-tag>
        </div>
        <div class="table-wrapper">
          <el-table
            :data="klineData"
            size="small"
            stripe
            height="100%"
            :header-cell-style="headerCellStyle"
            :cell-style="cellStyle"
          >
            <el-table-column prop="ts_code" label="股票代码" width="110" fixed="left" />
            <el-table-column label="开盘" width="90" align="right">
              <template #default="{ row }">
                <span class="number-cell">{{ formatNumber(row.open, 2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="最高" width="90" align="right">
              <template #default="{ row }">
                <span class="number-cell text-positive">{{ formatNumber(row.high, 2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="最低" width="90" align="right">
              <template #default="{ row }">
                <span class="number-cell text-negative">{{ formatNumber(row.low, 2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="收盘" width="90" align="right">
              <template #default="{ row }">
                <span class="number-cell" :class="{ 'text-positive': row.close >= row.open, 'text-negative': row.close < row.open }">
                  {{ formatNumber(row.close, 2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="成交量" width="110" align="right">
              <template #default="{ row }">
                <span class="number-cell">{{ formatVolume(row.volume) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="90" align="right">
              <template #default="{ row }">
                <span class="number-cell" :class="{ 'text-positive': row.price_change_pct >= 0, 'text-negative': row.price_change_pct < 0 }">
                  {{ formatPercent(row.price_change_pct) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="table-panel">
        <div class="panel-header">
          <span class="panel-title">实时因子更新</span>
          <el-tag type="warning" size="small">
            {{ factorData.length }} 条记录
          </el-tag>
        </div>
        <div class="table-wrapper">
          <el-table
            :data="factorData"
            size="small"
            stripe
            height="100%"
            :header-cell-style="headerCellStyle"
            :cell-style="cellStyle"
          >
            <el-table-column prop="ts_code" label="股票代码" width="110" fixed="left" />
            <el-table-column label="因子值" width="120" align="right">
              <template #default="{ row }">
                <span class="number-cell" :class="{ 'text-positive': row.factor_value > 0, 'text-negative': row.factor_value < 0 }">
                  {{ formatNumber(row.factor_value, 4) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="上期值" width="120" align="right">
              <template #default="{ row }">
                <span class="number-cell" :class="{ 'text-positive': row.previous > 0, 'text-negative': row.previous < 0 }">
                  {{ formatNumber(row.previous, 4) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="变化率" width="100" align="right">
              <template #default="{ row }">
                <span class="number-cell" :class="{ 'text-positive': row.change_pct >= 0, 'text-negative': row.change_pct < 0 }">
                  {{ formatPercent(row.change_pct) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, VideoStop, Calendar, TrendCharts, DataLine, Operation } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'
import { wsApi } from '../api'

const props = defineProps({
  workflow: {
    type: Object,
    required: true
  }
})

const workflowStore = useWorkflowStore()

const datasets = computed(() => workflowStore.datasets)

const selectedDataset = ref(null)
const pushInterval = ref(1.0)
const isConnected = ref(false)
const isConnecting = ref(false)
const isPaused = ref(false)
const ws = ref(null)
const currentDate = ref('')
const progressPercent = ref(0)
const totalSteps = ref(0)
const currentStep = ref(0)
const nStocks = ref(0)
const factorMean = ref(0)
const factorStd = ref(0)

const klineData = ref([])
const factorData = ref([])

const headerCellStyle = {
  background: '#1e293b',
  color: '#94a3b8',
  fontWeight: '500',
  borderColor: '#334155'
}

const cellStyle = {
  background: '#0f172a',
  color: '#e2e8f0',
  borderColor: '#1e293b'
}

const connectionStatusType = computed(() => {
  if (isConnecting.value) return 'warning'
  if (isConnected.value && isPaused.value) return 'info'
  if (isConnected.value) return 'success'
  return 'danger'
})

const connectionStatusText = computed(() => {
  if (isConnecting.value) return '连接中...'
  if (isConnected.value && isPaused.value) return '已暂停'
  if (isConnected.value) return '已连接'
  return '未连接'
})

function formatNumber(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(decimals)
}

function formatPercent(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  const sign = v >= 0 ? '+' : ''
  return sign + (v * 100).toFixed(2) + '%'
}

function formatVolume(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  if (v >= 100000000) {
    return (v / 100000000).toFixed(2) + '亿'
  } else if (v >= 10000) {
    return (v / 10000).toFixed(2) + '万'
  }
  return Number(v).toFixed(0)
}

function handleStart() {
  if (!selectedDataset.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  if (!props.workflow?.nodes?.length) {
    ElMessage.warning('请先构建工作流')
    return
  }
  connect()
}

function handlePause() {
  isPaused.value = true
  if (ws.value) {
    ws.value.send(JSON.stringify({ type: 'pause' }))
  }
}

function handleStop() {
  disconnect()
}

function connect() {
  if (isConnected.value || isConnecting.value) return
  
  isConnecting.value = true
  isPaused.value = false
  
  const url = wsApi.buildRealtimeUrl(
    selectedDataset.value,
    props.workflow,
    pushInterval.value
  )

  try {
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      isConnecting.value = false
      isConnected.value = true
      isPaused.value = false
      ElMessage.success('WebSocket 连接成功')
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('消息解析失败:', e)
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      ElMessage.error('WebSocket 连接错误')
    }

    ws.value.onclose = () => {
      isConnected.value = false
      isConnecting.value = false
      isPaused.value = false
      ws.value = null
    }
  } catch (e) {
    isConnecting.value = false
    ElMessage.error('连接失败: ' + e.message)
  }
}

function disconnect() {
  if (ws.value) {
    try {
      ws.value.close()
    } catch (e) {
      console.error('关闭连接失败:', e)
    }
    ws.value = null
  }
  isConnected.value = false
  isConnecting.value = false
  isPaused.value = false
}

function handleMessage(data) {
  switch (data.type) {
    case 'session_start':
      handleSessionStart(data)
      break
    case 'realtime_update':
      handleRealtimeUpdate(data)
      break
    case 'realtime_end':
      handleRealtimeEnd(data)
      break
    default:
      console.log('未知消息类型:', data.type)
  }
}

function handleSessionStart(data) {
  currentDate.value = data.start_date || ''
  totalSteps.value = data.total_steps || 0
  currentStep.value = 0
  progressPercent.value = 0
  klineData.value = []
  factorData.value = []
  nStocks.value = 0
  factorMean.value = 0
  factorStd.value = 0
  ElMessage.info(`实时推送开始，共 ${totalSteps.value} 个交易日`)
}

function handleRealtimeUpdate(data) {
  if (isPaused.value) return

  currentDate.value = data.trade_date || ''
  currentStep.value = data.step || currentStep.value + 1
  
  if (totalSteps.value > 0) {
    progressPercent.value = Math.min(100, Math.round((currentStep.value / totalSteps.value) * 100))
  }

  if (data.kline_data && Array.isArray(data.kline_data)) {
    klineData.value = [...data.kline_data.slice(0, 100)]
  }

  if (data.factor_data && Array.isArray(data.factor_data)) {
    factorData.value = [...data.factor_data.slice(0, 100)]
    
    const values = data.factor_data.map(f => f.factor_value).filter(v => v !== null && !isNaN(v))
    if (values.length > 0) {
      const mean = values.reduce((a, b) => a + b, 0) / values.length
      const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length
      factorMean.value = mean
      factorStd.value = Math.sqrt(variance)
    }
    
    nStocks.value = values.length
  }
}

function handleRealtimeEnd(data) {
  ElMessage.success('实时推送已完成')
  disconnect()
}

function resume() {
  isPaused.value = false
  if (ws.value) {
    ws.value.send(JSON.stringify({ type: 'resume' }))
  }
}

watch(isPaused, (val) => {
  if (!val && isConnected.value) {
    resume()
  }
})

onUnmounted(() => {
  disconnect()
})

defineExpose({
  connect,
  disconnect
})
</script>

<style scoped>
.realtime-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f172a;
  padding: 16px;
  gap: 16px;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e293b;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #334155;
}

.control-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.interval-unit {
  color: #94a3b8;
  font-size: 12px;
}

.control-right {
  display: flex;
  gap: 8px;
}

.progress-section {
  background: #1e293b;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #334155;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
}

.progress-value {
  color: #67c23a;
  font-size: 14px;
  font-weight: 600;
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.progress-percent {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 600;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card-dark {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  border-radius: 8px !important;
}

.stat-card-dark :deep(.el-card__body) {
  padding: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.date-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.stock-icon {
  background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
  color: #fff;
}

.mean-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
}

.std-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
}

.stat-info {
  flex: 1;
}

.stat-value-dark {
  font-size: 22px;
  font-weight: 700;
  color: #f1f5f9;
  font-family: 'JetBrains Mono', Consolas, monospace;
  line-height: 1.2;
}

.stat-label-dark {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.tables-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.table-panel {
  background: #1e293b;
  border-radius: 8px;
  border: 1px solid #334155;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #334155;
  background: #0f172a;
}

.panel-title {
  color: #f1f5f9;
  font-size: 14px;
  font-weight: 600;
}

.table-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-wrapper :deep(.el-table) {
  background: #0f172a;
}

.table-wrapper :deep(.el-table__row) {
  background: #0f172a;
}

.table-wrapper :deep(.el-table__row:hover > td) {
  background: #1e293b !important;
}

.table-wrapper :deep(.el-table--striped .el-table__row--striped td) {
  background: #162032;
}

.number-cell {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
}

.text-positive {
  color: #67c23a !important;
}

.text-negative {
  color: #f56c6c !important;
}

:deep(.el-progress-bar__outer) {
  background-color: #334155 !important;
  border-radius: 4px;
}

:deep(.el-progress-bar__inner) {
  border-radius: 4px;
}

:deep(.el-slider__runway) {
  background-color: #334155;
}

:deep(.el-slider__bar) {
  background-color: #409eff;
}

:deep(.el-slider__button) {
  border-color: #409eff;
}

:deep(.el-input__wrapper) {
  background-color: #0f172a;
  border-color: #334155;
}

:deep(.el-select__wrapper) {
  background-color: #0f172a;
  border-color: #334155;
}

:deep(.el-input__inner) {
  color: #e2e8f0;
}

:deep(.el-select__popper) {
  background: #1e293b;
  border: 1px solid #334155;
}

:deep(.el-select-dropdown__item) {
  color: #e2e8f0;
}

:deep(.el-select-dropdown__item:hover) {
  background: #334155;
}

:deep(.el-select-dropdown__item.selected) {
  color: #409eff;
  font-weight: 600;
}
</style>
