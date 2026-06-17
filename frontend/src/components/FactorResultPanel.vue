<template>
  <div>
    <div class="section-title">因子计算结果</div>

    <div class="flex flex-col gap-sm mb-md">
      <div class="stat-card success">
        <div class="stat-value">{{ formatNum(stats?.count, 0) }}</div>
        <div class="stat-label">数据点数量</div>
      </div>
      <div class="stat-card info">
        <div class="stat-value">{{ formatNum(stats?.n_stocks, 0) }}</div>
        <div class="stat-label">股票数量</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ formatNum(stats?.n_dates, 0) }}</div>
        <div class="stat-label">交易日数</div>
      </div>
    </div>

    <div class="sub-title">统计信息</div>
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="均值">{{ formatNum(stats?.mean, 4) }}</el-descriptions-item>
      <el-descriptions-item label="标准差">{{ formatNum(stats?.std, 4) }}</el-descriptions-item>
      <el-descriptions-item label="最小值">{{ formatNum(stats?.min, 4) }}</el-descriptions-item>
      <el-descriptions-item label="中位数">{{ formatNum(stats?.median, 4) }}</el-descriptions-item>
      <el-descriptions-item label="最大值">{{ formatNum(stats?.max, 4) }}</el-descriptions-item>
    </el-descriptions>

    <div class="mt-md">
      <div class="sub-title">操作</div>
      <div class="flex flex-col gap-sm">
        <el-button type="warning" style="width: 100%;" @click="runBacktest">
          <el-icon style="margin-right: 4px;"><Histogram /></el-icon>
          一键回测
        </el-button>
        <el-button type="primary" plain style="width: 100%;" @click="showResultViewer = true">
          <el-icon style="margin-right: 4px;"><View /></el-icon>
          查看详细结果
        </el-button>
        <el-button type="info" plain style="width: 100%;" @click="exportCsv">
          <el-icon style="margin-right: 4px;"><Download /></el-icon>
          导出CSV
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Histogram, View, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useWorkflowStore } from '../stores/workflow'
import { backtestApi } from '../api'

const workflowStore = useWorkflowStore()

const stats = computed(() => workflowStore.factorStats)
const showResultViewer = ref(false)

function formatNum(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

async function runBacktest() {
  try {
    const res = await backtestApi.runBacktest({
      factor_name: workflowStore.workflowName,
      factor_values: workflowStore.factorResult,
      dataset_name: workflowStore.currentDataset,
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
  }
}

function exportCsv() {
  if (!workflowStore.factorResult?.length) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  const header = Object.keys(workflowStore.factorResult[0]).join(',')
  const rows = workflowStore.factorResult.map(r => Object.values(r).join(','))
  const csv = [header, ...rows].join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `factor_result_${Date.now()}.csv`
  link.click()
  ElMessage.success('导出成功')
}
</script>
