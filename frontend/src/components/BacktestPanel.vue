<template>
  <div>
    <div class="section-title">回测结果</div>

    <div class="flex flex-col gap-sm mb-md">
      <div class="stat-card warning">
        <div class="stat-value">{{ pct(result?.ic_stats?.mean_ic) }}</div>
        <div class="stat-label">平均 IC</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ formatNum(result?.ic_stats?.icir, 2) }}</div>
        <div class="stat-label">ICIR</div>
      </div>
      <div class="stat-card info">
        <div class="stat-value">{{ pct(result?.long_short_return?.cumulative_return) }}</div>
        <div class="stat-label">多空收益</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ pct(result?.turnover_stats?.mean_turnover) }}</div>
        <div class="stat-label">平均换手率</div>
      </div>
    </div>

    <div class="sub-title">IC 指标详情</div>
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="平均 IC">{{ pct(result?.ic_stats?.mean_ic) }}</el-descriptions-item>
      <el-descriptions-item label="IC 标准差">{{ formatNum(result?.ic_stats?.ic_std, 4) }}</el-descriptions-item>
      <el-descriptions-item label="ICIR">{{ formatNum(result?.ic_stats?.icir, 3) }}</el-descriptions-item>
      <el-descriptions-item label="T统计量">{{ formatNum(result?.ic_stats?.t_stat, 3) }}</el-descriptions-item>
      <el-descriptions-item label="P值">{{ formatNum(result?.ic_stats?.p_value, 4) }}</el-descriptions-item>
    </el-descriptions>

    <div class="sub-title mt-md">分组收益表现</div>
    <el-table :data="result?.group_returns || []" size="small" stripe>
      <el-table-column prop="group" label="分组" width="60" align="center" />
      <el-table-column label="累计收益" width="90" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.cumulative_return >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ pct(row.cumulative_return) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="年化" width="80" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.annual_return >= 0 ? '#f56c6c' : '#67c23a' }">
            {{ pct(row.annual_return) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="夏普" width="60" align="right">
        <template #default="{ row }">{{ formatNum(row.sharpe_ratio, 2) }}</template>
      </el-table-column>
      <el-table-column label="回撤" width="70" align="right">
        <template #default="{ row }">
          <span style="color: #f56c6c;">{{ pct(row.max_drawdown) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-md">
      <div class="sub-title">操作</div>
      <el-button type="success" style="width: 100%;" @click="$emit('view-details')">
        <el-icon style="margin-right: 4px;"><TrendCharts /></el-icon>
        查看可视化图表
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { TrendCharts } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'

defineEmits(['view-details'])

const workflowStore = useWorkflowStore()
const result = computed(() => workflowStore.backtestResult)

function pct(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return (v * 100).toFixed(2) + '%'
}

function formatNum(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(decimals)
}
</script>
