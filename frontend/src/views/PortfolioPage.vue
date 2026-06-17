<template>
  <div class="page-container p-md">
    <div class="flex items-center justify-between mb-md">
      <h2 class="page-title">
        <el-icon :size="24" color="#409eff" class="mr-sm"><PieChart /></el-icon>
        投资组合优化分析
      </h2>
    </div>

    <el-row :gutter="16">
      <el-col :span="24" :lg="8">
        <el-card class="mb-md">
          <template #header>
            <div class="flex items-center gap-sm">
              <el-icon><Setting /></el-icon>
              <span>优化参数</span>
            </div>
          </template>

          <el-form label-position="top" size="default">
            <el-form-item label="数据集">
              <el-select v-model="params.datasetName" placeholder="请选择数据集" style="width: 100%;">
                <el-option
                  v-for="ds in datasets"
                  :key="ds.name"
                  :label="ds.name"
                  :value="ds.name"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="因子列表">
              <el-select
                v-model="params.factors"
                multiple
                placeholder="请选择因子"
                style="width: 100%;"
              >
                <el-option
                  v-for="factor in availableFactors"
                  :key="factor"
                  :label="factor"
                  :value="factor"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="优化模型">
              <el-select v-model="params.model" placeholder="请选择模型" style="width: 100%;">
                <el-option label="均值方差 (Mean Variance)" value="mean_variance" />
                <el-option label="风险平价 (Risk Parity)" value="risk_parity" />
                <el-option label="最小方差 (Min Variance)" value="min_variance" />
                <el-option label="等权重 (Equal Weight)" value="equal_weight" />
                <el-option label="最大夏普 (Max Sharpe)" value="max_sharpe" />
              </el-select>
            </el-form-item>

            <el-form-item label="目标收益率 (可选)">
              <el-input-number
                v-model="params.targetReturn"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="4"
                placeholder="留空自动优化"
                style="width: 100%;"
                :controls="false"
              />
              <div class="text-muted text-xs mt-xs">年化目标收益率，如 0.15 表示 15%</div>
            </el-form-item>

            <el-form-item label="无风险利率">
              <el-input-number
                v-model="params.riskFreeRate"
                :min="0"
                :max="0.2"
                :step="0.005"
                :precision="4"
                style="width: 100%;"
                :controls="false"
              />
              <div class="text-muted text-xs mt-xs">默认 3%，用于计算夏普比率</div>
            </el-form-item>

            <el-form-item :label="`最小单资产权重: ${(params.minWeight * 100).toFixed(1)}%`">
              <el-slider
                v-model="params.minWeight"
                :min="0"
                :max="params.maxWeight"
                :step="0.01"
                :show-tooltip="false"
              />
            </el-form-item>

            <el-form-item :label="`最大单资产权重: ${(params.maxWeight * 100).toFixed(1)}%`">
              <el-slider
                v-model="params.maxWeight"
                :min="params.minWeight"
                :max="1"
                :step="0.01"
                :show-tooltip="false"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="MagicStick"
                :loading="loading"
                @click="handleOptimize"
                style="width: 100%;"
                size="large"
              >
                {{ loading ? '优化中...' : '开始优化' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="24" :lg="16">
        <el-card v-if="result" class="mb-md">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-sm">
                <el-icon color="#67c23a"><TrendCharts /></el-icon>
                <span>有效前沿</span>
              </div>
              <el-tag size="small" type="success">
                蒙特卡洛模拟: {{ result.monte_carlo_points?.length || 0 }} 个点
              </el-tag>
            </div>
          </template>
          <div style="height: 450px;">
            <EfficientFrontierChart
              :monte_carlo_points="result.monte_carlo_points"
              :efficient_frontier="result.efficient_frontier"
              :optimal_point="result.optimal_point"
            />
          </div>
        </el-card>

        <el-card v-if="result?.optimal_point" class="mb-md">
          <template #header>
            <div class="flex items-center gap-sm">
              <el-icon color="#ff9900"><Star /></el-icon>
              <span>最优投资组合指标</span>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="metric-card success">
                <div class="metric-value">{{ pct(result.optimal_point.expected_return) }}</div>
                <div class="metric-label">预期年化收益率</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="metric-card warning">
                <div class="metric-value">{{ pct(result.optimal_point.expected_volatility) }}</div>
                <div class="metric-label">预期波动率</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="metric-card info">
                <div class="metric-value">{{ num(result.optimal_point.sharpe_ratio, 3) }}</div>
                <div class="metric-label">夏普比率</div>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="result?.optimal_point?.weights" class="mb-md">
          <template #header>
            <div class="flex items-center gap-sm">
              <el-icon color="#409eff"><Tickets /></el-icon>
              <span>最优资产权重配置</span>
            </div>
          </template>
          <el-table
            :data="weightsTableData"
            stripe
            style="width: 100%;"
            :default-sort="{ prop: 'weight', order: 'descending' }"
          >
            <el-table-column
              prop="asset"
              label="资产"
              min-width="120"
              align="left"
            />
            <el-table-column
              prop="weight"
              label="权重"
              width="140"
              align="right"
              sortable
            >
              <template #default="{ row }">
                <span :style="{ color: row.weight >= 0.1 ? '#67c23a' : '#606266', fontWeight: row.weight >= 0.1 ? 600 : 400 }">
                  {{ pct(row.weight) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="权重分布" min-width="200">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.weight * 100"
                  :show-text="false"
                  :stroke-width="12"
                  :color="getProgressColor(row.weight)"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card v-if="!result && !loading" class="mb-md">
          <el-empty
            description="请设置参数并点击「开始优化」按钮"
            :image-size="120"
          >
            <template #image>
              <el-icon :size="80" color="#c0c4cc"><DataLine /></el-icon>
            </template>
            <el-button type="primary" @click="handleOptimize">开始优化</el-button>
          </el-empty>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  PieChart,
  Setting,
  MagicStick,
  TrendCharts,
  Star,
  Tickets,
  DataLine
} from '@element-plus/icons-vue'
import { portfolioApi, dataApi } from '../api/index.js'
import EfficientFrontierChart from '../components/EfficientFrontierChart.vue'

const loading = ref(false)
const result = ref(null)
const datasets = ref([])
const availableFactors = ref([
  'momentum',
  'value',
  'quality',
  'size',
  'volatility',
  'liquidity',
  'growth',
  'profitability'
])

const params = reactive({
  datasetName: '',
  factors: ['momentum', 'value', 'quality'],
  model: 'mean_variance',
  riskFreeRate: 0.03,
  targetReturn: null,
  minWeight: 0,
  maxWeight: 0.3
})

const weightsTableData = computed(() => {
  if (!result.value?.optimal_point?.weights) return []
  return Object.entries(result.value.optimal_point.weights).map(([asset, weight]) => ({
    asset,
    weight
  }))
})

function pct(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return (v * 100).toFixed(2) + '%'
}

function num(v, d = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(d)
}

function getProgressColor(weight) {
  if (weight >= 0.2) return '#67c23a'
  if (weight >= 0.1) return '#409eff'
  if (weight >= 0.05) return '#e6a23c'
  return '#c0c4cc'
}

async function loadDatasets() {
  try {
    const data = await dataApi.listDatasets()
    datasets.value = data.datasets || []
    if (datasets.value.length > 0 && !params.datasetName) {
      params.datasetName = datasets.value[0].name
    }
  } catch (e) {
    console.error('Failed to load datasets:', e)
  }
}

async function handleOptimize() {
  if (!params.datasetName) {
    ElMessage.warning('请选择数据集')
    return
  }
  if (!params.factors || params.factors.length === 0) {
    ElMessage.warning('请至少选择一个因子')
    return
  }
  if (params.minWeight >= params.maxWeight) {
    ElMessage.warning('最小权重必须小于最大权重')
    return
  }

  loading.value = true
  try {
    const data = await portfolioApi.optimize(
      params.datasetName,
      params.factors,
      params.model,
      params.riskFreeRate,
      params.targetReturn,
      params.minWeight,
      params.maxWeight
    )

    if (data.success) {
      result.value = data
      ElMessage.success('优化完成！')
    } else {
      ElMessage.error(data.message || '优化失败')
    }
  } catch (e) {
    console.error('Optimization error:', e)
    ElMessage.error(e.message || '优化失败，请检查参数')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDatasets()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  overflow: auto;
  background: #f5f7fa;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.metric-card {
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  transition: transform 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
}

.metric-card.success {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.metric-card.warning {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.metric-card.info {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.metric-label {
  font-size: 13px;
  opacity: 0.9;
}

.text-muted {
  color: #909399;
}

.text-xs {
  font-size: 12px;
}

.mt-xs {
  margin-top: 4px;
}

.mr-sm {
  margin-right: 8px;
}

.mb-md {
  margin-bottom: 16px;
}

.mt-md {
  margin-top: 16px;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.justify-between {
  justify-content: space-between;
}

.gap-sm {
  gap: 8px;
}
</style>
