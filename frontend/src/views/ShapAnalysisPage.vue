<template>
  <div class="page-container p-md">
    <div class="flex items-center justify-between mb-md">
      <h2 class="page-title">SHAP 分析</h2>
      <div class="flex gap-sm">
        <el-button
          type="primary"
          :icon="Download"
          :disabled="!shapResult || isAnalyzing"
          @click="downloadReport"
        >
          下载 PDF 报告
        </el-button>
      </div>
    </div>

    <el-card class="mb-md">
      <div class="flex flex-wrap gap-md items-end">
        <div class="form-item">
          <label class="form-label">数据集</label>
          <el-select
            v-model="selectedDataset"
            placeholder="请选择数据集"
            style="width: 200px"
            size="default"
          >
            <el-option
              v-for="ds in datasets"
              :key="ds"
              :label="ds"
              :value="ds"
            />
          </el-select>
        </div>

        <div class="form-item">
          <label class="form-label">因子</label>
          <el-select
            v-model="selectedFactor"
            placeholder="请选择因子"
            style="width: 200px"
            size="default"
          >
            <el-option
              v-for="factor in computedFactors"
              :key="factor.id"
              :label="factor.name"
              :value="factor.id"
            />
          </el-select>
        </div>

        <div class="form-item">
          <label class="form-label">样本数量</label>
          <el-input-number
            v-model="nSamples"
            :min="10"
            :max="500"
            :step="10"
            size="default"
          />
        </div>

        <div class="form-item">
          <label class="form-label">目标周期</label>
          <el-input-number
            v-model="targetPeriod"
            :min="1"
            :max="60"
            :step="1"
            size="default"
          />
        </div>

        <el-button
          type="primary"
          :icon="DataAnalysis"
          :loading="isAnalyzing"
          :disabled="!selectedDataset || !selectedFactor"
          @click="runAnalysis"
          size="default"
        >
          {{ isAnalyzing ? '分析中...' : '开始分析' }}
        </el-button>
      </div>
    </el-card>

    <el-row :gutter="16" v-if="!shapResult && !isAnalyzing">
      <el-col :span="24">
        <el-card class="text-center py-lg">
          <el-empty description="请选择数据集和因子，然后点击开始分析" />
        </el-card>
      </el-col>
    </el-row>

    <div v-else-if="isAnalyzing" class="mb-md">
      <el-card class="text-center py-lg">
        <el-icon class="is-loading mb-sm" :size="48" color="#409eff"><Loading /></el-icon>
        <div class="text-muted">正在进行 SHAP 分析，请稍候...</div>
      </el-card>
    </div>

    <template v-else-if="shapResult">
      <el-card class="mb-md">
        <template #header>
          <div class="flex items-center gap-sm">
            <el-icon color="#409eff"><TrendCharts /></el-icon>
            <span class="section-title-no-border">样本预测解释 - 力导向图</span>
          </div>
        </template>
        <div class="flex flex-wrap gap-md mb-md">
          <div class="form-item">
            <label class="form-label">选择样本</label>
            <el-select
              v-model="selectedSampleIndex"
              style="width: 200px"
              size="small"
            >
              <el-option
                v-for="(sample, idx) in shapResult.sample_predictions || []"
                :key="idx"
                :label="`样本 ${idx + 1}: ${sample.predicted.toFixed(4)}`"
                :value="idx"
              />
            </el-select>
          </div>
        </div>
        <ShapForcePlot
          v-if="selectedSample"
          :data="selectedSample"
          :predicted="selectedSamplePredicted"
        />
      </el-card>

      <el-row :gutter="16" class="mb-md">
        <el-col :span="24">
          <el-card>
            <template #header>
              <div class="flex items-center gap-sm">
                <el-icon color="#67c23a"><Histogram /></el-icon>
                <span class="section-title-no-border">特征重要性排名 (平均 |SHAP| 值)</span>
              </div>
            </template>
            <div ref="featureImportanceChart" class="chart-container" style="height: 400px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mb-md">
        <el-col :span="24">
          <el-card>
            <template #header>
              <div class="flex items-center gap-sm">
                <el-icon color="#e6a23c"><DataLine /></el-icon>
                <span class="section-title-no-border">SHAP 摘要图 (Beeswarm)</span>
              </div>
            </template>
            <div class="text-muted mb-sm">
              每个点代表一个样本，颜色表示特征值大小，位置表示 SHAP 值
            </div>
            <div ref="summaryPlot" class="chart-container" style="height: 500px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-card>
        <template #header>
          <div class="flex items-center gap-sm">
            <el-icon color="#f56c6c"><InfoFilled /></el-icon>
            <span class="section-title-no-border">分析摘要</span>
          </div>
        </template>
        <div class="grid-container">
          <div class="stat-card">
            <div class="stat-value">{{ shapResult.summary?.total_samples || 0 }}</div>
            <div class="stat-label">分析样本数</div>
          </div>
          <div class="stat-card success">
            <div class="stat-value">{{ shapResult.summary?.feature_count || 0 }}</div>
            <div class="stat-label">特征数量</div>
          </div>
          <div class="stat-card warning">
            <div class="stat-value">{{ formatPct(shapResult.summary?.mean_abs_shap) }}</div>
            <div class="stat-label">平均 |SHAP| 值</div>
          </div>
          <div class="stat-card info">
            <div class="stat-value">{{ formatNum(shapResult.summary?.base_value) }}</div>
            <div class="stat-label">基准值 (Base Value)</div>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import {
  Download,
  DataAnalysis,
  Loading,
  TrendCharts,
  Histogram,
  DataLine,
  InfoFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWorkflowStore } from '../stores/workflow'
import { dataApi, shapApi } from '../api/index'
import ShapForcePlot from '../components/ShapForcePlot.vue'
import * as d3 from 'd3'

const workflowStore = useWorkflowStore()

const datasets = ref([])
const selectedDataset = ref('')
const selectedFactor = ref('')
const nSamples = ref(100)
const targetPeriod = ref(5)
const isAnalyzing = ref(false)
const shapResult = ref(null)
const selectedSampleIndex = ref(0)

const featureImportanceChart = ref(null)
const summaryPlot = ref(null)

const computedFactors = computed(() => {
  return workflowStore.nodes.map(node => ({
    id: node.id,
    name: node.name
  }))
})

const selectedSample = computed(() => {
  if (!shapResult.value?.sample_predictions) return null
  return shapResult.value.sample_predictions[selectedSampleIndex.value]
})

const selectedSamplePredicted = computed(() => {
  return selectedSample.value?.predicted || 0
})

function formatNum(v, d = 4) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(d)
}

function formatPct(v, d = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return (v * 100).toFixed(d) + '%'
}

async function loadDatasets() {
  try {
    const data = await dataApi.listDatasets()
    datasets.value = data || []
    if (datasets.value.length > 0 && !selectedDataset.value) {
      selectedDataset.value = datasets.value[0]
    }
  } catch (err) {
    console.error('Failed to load datasets:', err)
    ElMessage.error('加载数据集失败')
  }
}

async function runAnalysis() {
  if (!selectedDataset.value || !selectedFactor.value) {
    ElMessage.warning('请选择数据集和因子')
    return
  }

  const node = workflowStore.getNodeById(selectedFactor.value)
  if (!node) {
    ElMessage.error('找不到选中的因子节点')
    return
  }

  const factorValues = workflowStore.factorResult
  if (!factorValues) {
    ElMessage.warning('请先运行因子计算')
    return
  }

  isAnalyzing.value = true
  shapResult.value = null

  try {
    const result = await shapApi.analyze(
      selectedDataset.value,
      node.name,
      factorValues,
      nSamples.value,
      targetPeriod.value
    )

    shapResult.value = result
    selectedSampleIndex.value = 0

    await nextTick()
    setTimeout(() => {
      renderFeatureImportanceChart()
      renderSummaryPlot()
    }, 100)

    ElMessage.success('SHAP 分析完成')
  } catch (err) {
    console.error('SHAP analysis failed:', err)
    ElMessage.error('SHAP 分析失败: ' + (err.message || '未知错误'))
  } finally {
    isAnalyzing.value = false
  }
}

async function downloadReport() {
  if (!shapResult.value) {
    ElMessage.warning('请先进行 SHAP 分析')
    return
  }

  try {
    const node = workflowStore.getNodeById(selectedFactor.value)
    const blob = await shapApi.generateReport(
      node?.name || 'Factor',
      shapResult.value,
      workflowStore.backtestResult
    )

    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `shap_report_${Date.now()}.pdf`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('PDF 报告下载成功')
  } catch (err) {
    console.error('Failed to generate report:', err)
    ElMessage.error('生成 PDF 报告失败: ' + (err.message || '未知错误'))
  }
}

function setupChart(container, margin = { top: 30, right: 30, bottom: 50, left: 120 }) {
  const node = container
  d3.select(node).selectAll('*').remove()

  const rect = node.getBoundingClientRect()
  const width = rect.width - margin.left - margin.right
  const height = rect.height - margin.top - margin.bottom

  const svg = d3.select(node)
    .append('svg')
    .attr('width', rect.width)
    .attr('height', rect.height)

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  return { svg, g, width, height }
}

function addTooltip(svg) {
  return d3.select('body').append('div')
    .attr('class', 'chart-tooltip')
    .style('opacity', 0)
}

function renderFeatureImportanceChart() {
  const container = featureImportanceChart.value
  if (!container || !shapResult.value?.feature_importance) return

  const { svg, g, width, height } = setupChart(container, { top: 20, right: 30, bottom: 40, left: 150 })
  const tooltip = addTooltip(svg)

  const data = [...shapResult.value.feature_importance]
    .sort((a, b) => b.mean_abs_shap - a.mean_abs_shap)
    .slice(0, 20)

  const y = d3.scaleBand()
    .domain(data.map(d => d.feature_name))
    .range([0, height])
    .padding(0.2)

  const maxVal = d3.max(data, d => d.mean_abs_shap) || 1
  const x = d3.scaleLinear()
    .domain([0, maxVal * 1.1])
    .range([0, width])

  const colorScale = d3.scaleLinear()
    .domain([0, maxVal])
    .range(['#90caf9', '#1976d2'])

  g.selectAll('.bar')
    .data(data)
    .enter()
    .append('rect')
    .attr('class', 'bar')
    .attr('x', 0)
    .attr('y', d => y(d.feature_name))
    .attr('width', d => x(d.mean_abs_shap))
    .attr('height', y.bandwidth())
    .attr('fill', d => colorScale(d.mean_abs_shap))
    .attr('rx', 3)
    .attr('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this).attr('opacity', 0.8)
      tooltip.html(`
        <div style="font-weight: 600; margin-bottom: 4px;">${d.feature_name}</div>
        <div>平均 |SHAP|: ${formatNum(d.mean_abs_shap)}</div>
        <div>正向贡献: ${formatNum(d.positive_contribution)}</div>
        <div>负向贡献: ${formatNum(d.negative_contribution)}</div>
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 12) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', function() {
      d3.select(this).attr('opacity', 1)
      tooltip.style('opacity', 0)
    })

  g.selectAll('.bar-label')
    .data(data)
    .enter()
    .append('text')
    .attr('class', 'bar-label')
    .attr('x', d => x(d.mean_abs_shap) + 8)
    .attr('y', d => y(d.feature_name) + y.bandwidth() / 2 + 4)
    .attr('fill', '#606266')
    .attr('font-size', '11px')
    .text(d => formatNum(d.mean_abs_shap, 4))

  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .attr('font-size', '11px')
    .attr('fill', '#606266')

  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(6))

  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.3)
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).tickSize(-height).tickFormat(''))
}

function renderSummaryPlot() {
  const container = summaryPlot.value
  if (!container || !shapResult.value?.summary_data) return

  const { svg, g, width, height } = setupChart(container, { top: 30, right: 60, bottom: 50, left: 150 })
  const tooltip = addTooltip(svg)

  const summaryData = shapResult.value.summary_data
  const features = [...new Set(summaryData.map(d => d.feature_name))]
    .sort((a, b) => {
      const aMean = d3.mean(summaryData.filter(d => d.feature_name === a), d => Math.abs(d.shap_value))
      const bMean = d3.mean(summaryData.filter(d => d.feature_name === b), d => Math.abs(d.shap_value))
      return bMean - aMean
    })

  const y = d3.scaleBand()
    .domain(features)
    .range([0, height])
    .padding(0.3)

  const allShapValues = summaryData.map(d => d.shap_value)
  const maxAbsShap = d3.max(allShapValues, Math.abs) || 1
  const x = d3.scaleLinear()
    .domain([-maxAbsShap * 1.1, maxAbsShap * 1.1])
    .range([0, width])

  const allFeatureValues = summaryData.map(d => d.feature_value).filter(v => !isNaN(v))
  const minFeatureVal = d3.min(allFeatureValues)
  const maxFeatureVal = d3.max(allFeatureValues)
  const colorScale = d3.scaleLinear()
    .domain([minFeatureVal, (minFeatureVal + maxFeatureVal) / 2, maxFeatureVal])
    .range(['#409eff', '#e0e0e0', '#f56c6c'])

  g.append('line')
    .attr('x1', x(0))
    .attr('x2', x(0))
    .attr('y1', 0)
    .attr('y2', height)
    .attr('stroke', '#909399')
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '3,3')

  const simulation = d3.forceSimulation(summaryData)
    .force('x', d3.forceX(d => x(d.shap_value)).strength(0.3))
    .force('y', d3.forceY(d => y(d.feature_name) + y.bandwidth() / 2).strength(0.8))
    .force('collide', d3.forceCollide(4))
    .stop()

  for (let i = 0; i < 50; i++) simulation.tick()

  g.selectAll('.bead')
    .data(summaryData)
    .enter()
    .append('circle')
    .attr('class', 'bead')
    .attr('cx', d => Math.max(5, Math.min(width - 5, d.x)))
    .attr('cy', d => Math.max(5, Math.min(height - 5, d.y)))
    .attr('r', 3)
    .attr('fill', d => isNaN(d.feature_value) ? '#c0c4cc' : colorScale(d.feature_value))
    .attr('opacity', 0.7)
    .attr('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', 5).attr('opacity', 1)
      tooltip.html(`
        <div style="font-weight: 600; margin-bottom: 4px;">${d.feature_name}</div>
        <div>特征值: ${formatNum(d.feature_value)}</div>
        <div>SHAP 值: <span style="color: ${d.shap_value >= 0 ? '#f56c6c' : '#409eff'}; font-weight: 500;">${formatNum(d.shap_value)}</span></div>
        <div>影响: ${d.shap_value >= 0 ? '推高预测' : '拉低预测'}</div>
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 12) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', function() {
      d3.select(this).attr('r', 3).attr('opacity', 0.7)
      tooltip.style('opacity', 0)
    })

  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .attr('font-size', '11px')
    .attr('fill', '#606266')

  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(8).tickFormat(d => formatNum(d, 3)))

  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.3)
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).tickSize(-height).tickFormat(''))

  const legendX = width + 15
  const legendY = 0
  const legendHeight = 200

  const defs = svg.append('defs')
  const legendGradient = defs.append('linearGradient')
    .attr('id', 'summary-legend-gradient')
    .attr('x1', '0%').attr('y1', '100%')
    .attr('x2', '0%').attr('y2', '0%')

  legendGradient.append('stop').attr('offset', '0%').attr('stop-color', '#409eff')
  legendGradient.append('stop').attr('offset', '50%').attr('stop-color', '#e0e0e0')
  legendGradient.append('stop').attr('offset', '100%').attr('stop-color', '#f56c6c')

  g.append('rect')
    .attr('x', legendX)
    .attr('y', legendY)
    .attr('width', 16)
    .attr('height', legendHeight)
    .style('fill', 'url(#summary-legend-gradient)')
    .attr('rx', 2)

  const legendScale = d3.scaleLinear()
    .domain([minFeatureVal, maxFeatureVal])
    .range([legendHeight, 0])

  g.append('g')
    .attr('transform', `translate(${legendX + 22}, ${legendY})`)
    .attr('class', 'axis')
    .call(d3.axisRight(legendScale).ticks(5).tickFormat(d => formatNum(d, 2)))
    .selectAll('text')
    .attr('font-size', '10px')

  g.append('text')
    .attr('x', legendX - 5)
    .attr('y', legendY - 8)
    .attr('text-anchor', 'end')
    .attr('fill', '#606266')
    .attr('font-size', '11px')
    .attr('font-weight', '500')
    .text('特征值')
}

watch(selectedSampleIndex, () => {
  if (shapResult.value) {
    nextTick(() => {
      renderFeatureImportanceChart()
      renderSummaryPlot()
    })
  }
})

onMounted(async () => {
  await loadDatasets()
  
  if (workflowStore.selectedFactorForShap) {
    if (workflowStore.currentDataset && !selectedDataset.value) {
      selectedDataset.value = workflowStore.currentDataset
    }
    if (workflowStore.nodes.length > 0 && !selectedFactor.value) {
      selectedFactor.value = workflowStore.outputNodeId || workflowStore.nodes[0].id
    }
    if (workflowStore.factorResult) {
      setTimeout(() => {
        if (selectedDataset.value && selectedFactor.value) {
          runAnalysis()
        }
      }, 300)
    }
  }
})
</script>

<style scoped>
.page-container {
  height: 100%;
  overflow: auto;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.py-lg {
  padding: 48px 0;
}

.section-title-no-border {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-container {
  width: 100%;
  height: 100%;
}

:deep(.axis line),
:deep(.axis path) {
  stroke: #dcdfe6;
}

:deep(.axis text) {
  fill: #909399;
  font-size: 11px;
}

:deep(.grid line) {
  stroke: #f0f2f5;
  stroke-dasharray: 3, 3;
}
</style>
