<template>
  <el-drawer
    v-model="visible"
    title="回测可视化分析"
    direction="btt"
    size="85vh"
    :with-header="false"
    :destroy-on-close="false"
  >
    <div class="viewer-container flex flex-col" style="height: 100%;">
      <div class="flex items-center justify-between p-md" style="background: #fff; border-bottom: 1px solid var(--border-color);">
        <div class="flex items-center gap-md">
          <el-icon :size="22" color="#409eff"><DataAnalysis /></el-icon>
          <h2 style="margin: 0; font-size: 18px; font-weight: 600;">回测可视化分析</h2>
        </div>
        <div class="flex items-center gap-sm">
          <el-tag v-if="result?.success" type="success" size="small">回测成功</el-tag>
          <el-tag v-else type="danger" size="small">回测失败</el-tag>
          <el-button size="small" @click="visible = false" :icon="Close">关闭</el-button>
        </div>
      </div>

      <div class="flex-1 p-md" style="overflow: auto; background: #f5f7fa;">
        <div v-if="!result" class="flex-center flex-1" style="min-height: 400px;">
          <el-empty description="暂无回测结果，请先运行回测" />
        </div>

        <template v-else>
          <div class="card p-md mb-md">
            <div class="section-title">核心指标概览</div>
            <div class="flex flex-wrap gap-md">
              <div class="stat-card">
                <div class="stat-value">{{ pct(result.ic_stats?.mean_ic) }}</div>
                <div class="stat-label">平均 IC</div>
              </div>
              <div class="stat-card success">
                <div class="stat-value">{{ num(result.ic_stats?.icir, 2) }}</div>
                <div class="stat-label">ICIR (信息比率)</div>
              </div>
              <div class="stat-card warning">
                <div class="stat-value">{{ num(result.ic_stats?.t_stat, 2) }}</div>
                <div class="stat-label">T统计量</div>
              </div>
              <div class="stat-card info">
                <div class="stat-value">{{ pct(result.turnover_stats?.mean_turnover) }}</div>
                <div class="stat-label">平均换手率</div>
              </div>
              <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-value">{{ pct(longShortReturn) }}</div>
                <div class="stat-label">多空组合收益</div>
              </div>
            </div>
          </div>

          <div class="grid-container mb-md">
            <div class="card p-md">
              <div class="section-title">分组累计收益曲线</div>
              <div ref="cumReturnChart" class="chart-container" style="height: 320px;"></div>
            </div>
            <div class="card p-md">
              <div class="section-title">IC 时序变化</div>
              <div ref="icChart" class="chart-container" style="height: 320px;"></div>
            </div>
          </div>

          <div class="grid-container mb-md">
            <div class="card p-md">
              <div class="section-title">分组收益热力图</div>
              <div ref="heatmapChart" class="chart-container" style="height: 320px;"></div>
            </div>
            <div class="card p-md">
              <div class="section-title">换手率变化</div>
              <div ref="turnoverChart" class="chart-container" style="height: 320px;"></div>
            </div>
          </div>

          <div class="card p-md mb-md">
            <div class="section-title">多空组合收益曲线</div>
            <div ref="longShortChart" class="chart-container" style="height: 280px;"></div>
          </div>

          <div class="card p-md">
            <div class="section-title">分组详细指标</div>
            <el-table :data="result.group_returns || []" stripe size="default">
              <el-table-column prop="group" label="分组" width="80" align="center">
                <template #default="{ row }">
                  <el-tag
                    :type="row.group === 1 ? 'danger' : row.group === (result.group_returns?.length || 5) ? 'success' : 'info'"
                    size="small"
                  >
                    {{ row.group === 1 ? '最小' : row.group === (result.group_returns?.length || 5) ? '最大' : 'G' + row.group }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="累计收益" width="120" align="right">
                <template #default="{ row }">
                  <span :style="{ color: row.cumulative_return >= 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
                    {{ pct(row.cumulative_return) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="年化收益" width="120" align="right">
                <template #default="{ row }">
                  <span :style="{ color: row.annual_return >= 0 ? '#f56c6c' : '#67c23a' }">
                    {{ pct(row.annual_return) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="夏普比率" width="100" align="right">
                <template #default="{ row }">
                  <span :style="{ color: row.sharpe_ratio > 1 ? '#67c23a' : row.sharpe_ratio > 0 ? '#e6a23c' : '#909399' }">
                    {{ num(row.sharpe_ratio, 2) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="最大回撤" width="110" align="right">
                <template #default="{ row }">
                  <span style="color: #f56c6c;">{{ pct(row.max_drawdown) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="数据点数" width="100" align="center">
                <template #default="{ row }">{{ row.cumulative_returns?.length || 0 }}</template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { Close, DataAnalysis } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'
import * as d3 from 'd3'

const workflowStore = useWorkflowStore()
const visible = ref(false)

const result = computed(() => workflowStore.backtestResult)

const longShortReturn = computed(() =>
  result.value?.long_short_return?.cumulative_return || 0
)

function pct(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return (v * 100).toFixed(2) + '%'
}

function num(v, d = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(d)
}

const cumReturnChart = ref(null)
const icChart = ref(null)
const heatmapChart = ref(null)
const turnoverChart = ref(null)
const longShortChart = ref(null)

watch(visible, async (val) => {
  if (val && result.value?.success) {
    await nextTick()
    setTimeout(() => {
      renderCumReturnChart()
      renderICChart()
      renderHeatmap()
      renderTurnoverChart()
      renderLongShortChart()
    }, 100)
  }
})

function getColorForGroup(g, total) {
  const scale = d3.scaleLinear()
    .domain([1, total])
    .range(['#f56c6c', '#67c23a'])
    .interpolate(d3.interpolateHcl)
  return scale(g)
}

function setupChart(container, margin = { top: 30, right: 30, bottom: 50, left: 60 }) {
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

function renderCumReturnChart() {
  const container = cumReturnChart.value
  if (!container || !result.value?.group_returns) return
  
  const { svg, g, width, height } = setupChart(container)
  const tooltip = addTooltip(svg)
  const groups = result.value.group_returns
  
  const parseDate = d3.timeParse('%Y-%m-%d')
  const allDates = groups[0]?.cumulative_returns?.map(r => parseDate(r.trade_date)) || []
  if (allDates.length === 0) return
  
  const x = d3.scaleTime()
    .domain(d3.extent(allDates))
    .range([0, width])
  
  let maxRet = 0, minRet = 0
  groups.forEach(gr => {
    gr.cumulative_returns.forEach(r => {
      maxRet = Math.max(maxRet, r.cumulative_return)
      minRet = Math.min(minRet, r.cumulative_return)
    })
  })
  const pad = (maxRet - minRet) * 0.1 || 0.01
  
  const y = d3.scaleLinear()
    .domain([minRet - pad, maxRet + pad])
    .range([height, 0])
  
  const totalGroups = groups.length
  const fmt = d3.format('.2%')
  
  groups.forEach(grp => {
    const color = getColorForGroup(grp.group, totalGroups)
    const data = grp.cumulative_returns.map(r => ({
      date: parseDate(r.trade_date),
      value: r.cumulative_return
    })).filter(d => d.date)
    
    const line = d3.line()
      .x(d => x(d.date))
      .y(d => y(d.value))
      .curve(d3.curveMonotoneX)
    
    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 2)
      .attr('d', line)
      .on('mouseover', function(event, d) {
        d3.select(this).attr('stroke-width', 3.5)
        tooltip.html(`<strong>分组 ${grp.group}</strong>`)
          .style('opacity', 1)
      })
      .on('mousemove', function(event) {
        tooltip
          .style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-width', 2)
        tooltip.style('opacity', 0)
      })
  })
  
  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(8))
  
  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y).tickFormat(d3.format('.1%')))
  
  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.3)
    .call(d3.axisLeft(y).tickSize(-width).tickFormat(''))
  
  g.append('line')
    .attr('x1', 0)
    .attr('x2', width)
    .attr('y1', y(0))
    .attr('y2', y(0))
    .attr('stroke', '#909399')
    .attr('stroke-dasharray', '3,3')
  
  const legend = g.append('g')
    .attr('transform', `translate(${width - 120}, 10)`)
    .attr('class', 'legend')
  
  legend.append('rect')
    .attr('width', 110)
    .attr('height', 20 + totalGroups * 18)
    .attr('fill', '#fff')
    .attr('stroke', '#e4e7ed')
    .attr('rx', 4)
  
  groups.forEach((grp, i) => {
    const row = legend.append('g').attr('transform', `translate(8, ${14 + i * 18})`)
    row.append('circle')
      .attr('cx', 5)
      .attr('cy', 0)
      .attr('r', 5)
      .attr('fill', getColorForGroup(grp.group, totalGroups))
    row.append('text')
      .attr('x', 16)
      .attr('y', 4)
      .text(`Group ${grp.group}`)
      .attr('font-size', '11px')
  })
}

function renderICChart() {
  const container = icChart.value
  if (!container || !result.value?.ic_stats) return
  
  const { svg, g, width, height } = setupChart(container)
  const tooltip = addTooltip(svg)
  
  const icData = result.value.ic_stats.ic_values
  const parseDate = d3.timeParse('%Y-%m-%d')
  const data = icData.map(r => ({
    date: parseDate(r.trade_date),
    ic: r.ic,
    p: r.p_value
  })).filter(d => d.date)
  
  if (data.length === 0) return
  
  const x = d3.scaleTime()
    .domain(d3.extent(data, d => d.date))
    .range([0, width])
  
  const maxAbs = d3.max(data, d => Math.abs(d.ic)) || 0.1
  
  const y = d3.scaleLinear()
    .domain([-maxAbs * 1.1, maxAbs * 1.1])
    .range([height, 0])
  
  const colorScale = d3.scaleLinear()
    .domain([-maxAbs, 0, maxAbs])
    .range(['#67c23a', '#c0c4cc', '#f56c6c'])
  
  g.selectAll('.ic-bar')
    .data(data)
    .enter()
    .append('rect')
    .attr('class', 'ic-bar')
    .attr('x', d => x(d.date) - 1.5)
    .attr('y', d => d.ic >= 0 ? y(d.ic) : y(0))
    .attr('width', Math.max(1, width / data.length - 1))
    .attr('height', d => Math.abs(y(0) - y(d.ic)))
    .attr('fill', d => colorScale(d.ic))
    .attr('opacity', d => d.p < 0.05 ? 1 : 0.4)
    .on('mouseover', function(event, d) {
      tooltip.html(`
        <div>日期: ${d.trade_date}</div>
        <div>IC: ${(d.ic * 100).toFixed(2)}%</div>
        <div>P值: ${d.p.toFixed(4)}</div>
        <div>${d.p < 0.05 ? '显著' : '不显著'}</div>
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 12) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', function() {
      tooltip.style('opacity', 0)
    })
  
  const meanIC = result.value.ic_stats.mean_ic
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(meanIC)).attr('y2', y(meanIC))
    .attr('stroke', '#409eff')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '5,3')
  
  g.append('text')
    .attr('x', width - 80)
    .attr('y', y(meanIC) - 5)
    .attr('fill', '#409eff')
    .attr('font-size', '11px')
    .text(`Mean=${(meanIC * 100).toFixed(2)}%`)
  
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(0)).attr('y2', y(0))
    .attr('stroke', '#909399')
    .attr('stroke-width', 1)
  
  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(8))
  
  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y).tickFormat(d3.format('.1%')))
}

function renderHeatmap() {
  const container = heatmapChart.value
  if (!container || !result.value?.heatmap_data) return
  
  const { svg, g, width, height } = setupChart(container, { top: 30, right: 60, bottom: 50, left: 60 })
  const tooltip = addTooltip(svg)
  
  const data = result.value.heatmap_data
  if (!data || data.length === 0) return
  
  const parseDate = d3.timeParse('%Y-%m-%d')
  const dates = [...new Set(data.map(d => d.trade_date))].sort()
  const groups = [...new Set(data.map(d => d.group))].sort((a, b) => a - b)
  
  const dataMap = {}
  data.forEach(d => {
    if (!dataMap[d.trade_date]) dataMap[d.trade_date] = {}
    dataMap[d.trade_date][d.group] = d.return
  })
  
  const cellWidth = Math.max(1, width / dates.length - 1)
  const cellHeight = Math.max(5, height / groups.length - 1)
  
  const displayCount = Math.min(60, dates.length)
  const step = Math.ceil(dates.length / displayCount)
  const displayDates = dates.filter((_, i) => i % step === 0)
  
  const vals = data.map(d => d.return).filter(v => !isNaN(v))
  const maxAbs = d3.max(vals, Math.abs) || 0.05
  
  const color = d3.scaleDiverging()
    .domain([-maxAbs, 0, maxAbs])
    .interpolator(d3.interpolateRdYlGn)
  
  const dx = width / displayDates.length
  const dy = height / groups.length
  
  displayDates.forEach((date, i) => {
    groups.forEach((grp, j) => {
      const ret = dataMap[date]?.[grp]
      if (ret === undefined || isNaN(ret)) return
      
      g.append('rect')
        .attr('x', i * dx)
        .attr('y', j * dy)
        .attr('width', Math.max(1, dx - 1))
        .attr('height', Math.max(1, dy - 1))
        .attr('fill', color(ret))
        .attr('rx', 1)
        .on('mouseover', function(event) {
          tooltip.html(`
            <div>日期: ${date}</div>
            <div>分组: ${grp}</div>
            <div>收益: ${(ret * 100).toFixed(3)}%</div>
          `).style('opacity', 1)
        })
        .on('mousemove', function(event) {
          tooltip
            .style('left', (event.pageX + 12) + 'px')
            .style('top', (event.pageY - 28) + 'px')
        })
        .on('mouseout', function() {
          tooltip.style('opacity', 0)
        })
    })
  })
  
  const xScale = d3.scaleBand()
    .domain(displayDates.filter((_, i) => i % Math.ceil(displayDates.length / 8) === 0))
    .range([0, width])
  
  const yScale = d3.scaleBand()
    .domain(groups.map(String))
    .range([0, height])
    .padding(0.1)
  
  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(xScale))
  
  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(yScale))
  
  const defs = svg.append('defs')
  const gradient = defs.append('linearGradient')
    .attr('id', 'heatmap-gradient')
    .attr('x1', '0%').attr('y1', '0%')
    .attr('x2', '100%').attr('y2', '0%')
  
  const stops = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs]
  stops.forEach((s, i) => {
    gradient.append('stop')
      .attr('offset', `${i * 25}%`)
      .attr('stop-color', color(s))
  })
  
  const legendX = width + 10
  g.append('rect')
    .attr('x', legendX)
    .attr('y', 0)
    .attr('width', 16)
    .attr('height', height)
    .style('fill', 'url(#heatmap-gradient)')
  
  const lScale = d3.scaleLinear()
    .domain([-maxAbs, maxAbs])
    .range([height, 0])
  
  g.append('g')
    .attr('transform', `translate(${legendX + 20}, 0)`)
    .call(d3.axisRight(lScale).ticks(5).tickFormat(d3.format('.1%')))
    .selectAll('text')
    .attr('font-size', '10px')
}

function renderTurnoverChart() {
  const container = turnoverChart.value
  if (!container || !result.value?.turnover_stats) return
  
  const { svg, g, width, height } = setupChart(container)
  const tooltip = addTooltip(svg)
  
  const parseDate = d3.timeParse('%Y-%m-%d')
  const data = result.value.turnover_stats.turnover_by_period
    .map(r => ({ date: parseDate(r.trade_date), value: r.turnover }))
    .filter(d => d.date)
  
  if (data.length === 0) return
  
  const x = d3.scaleTime()
    .domain(d3.extent(data, d => d.date))
    .range([0, width])
  
  const maxV = d3.max(data, d => d.value) || 1
  
  const y = d3.scaleLinear()
    .domain([0, maxV * 1.1])
    .range([height, 0])
  
  const avg = result.value.turnover_stats.mean_turnover
  
  g.append('path')
    .datum(data)
    .attr('fill', 'rgba(64, 158, 255, 0.15)')
    .attr('stroke', '#409eff')
    .attr('stroke-width', 1.5)
    .attr('d', d3.area()
      .x(d => x(d.date))
      .y0(height)
      .y1(d => y(d.value))
      .curve(d3.curveMonotoneX)
    )
  
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(avg)).attr('y2', y(avg))
    .attr('stroke', '#e6a23c')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '5,3')
  
  g.append('text')
    .attr('x', 5)
    .attr('y', y(avg) - 5)
    .attr('fill', '#e6a23c')
    .attr('font-size', '11px')
    .text(`平均: ${(avg * 100).toFixed(1)}%`)
  
  const bisect = d3.bisector(d => d.date).center
  const focus = g.append('g').style('display', 'none')
  focus.append('line').attr('stroke', '#909399').attr('stroke-dasharray', '3,3').attr('y1', 0).attr('y2', height)
  focus.append('circle').attr('r', 4).attr('fill', '#409eff').attr('stroke', '#fff')
  
  svg.on('mouseover', () => focus.style('display', null))
    .on('mouseout', () => focus.style('display', 'none'))
    .on('mousemove', function(event) {
      const [mx] = d3.pointer(event)
      const mx0 = mx - 60
      const i = bisect(data, x.invert(Math.max(0, Math.min(width, mx0))))
      if (i >= 0 && i < data.length) {
        const d = data[i]
        focus.select('line').attr('x1', x(d.date)).attr('x2', x(d.date))
        focus.select('circle').attr('cx', x(d.date)).attr('cy', y(d.value))
        tooltip.html(`
          <div>日期: ${d.trade_date}</div>
          <div>换手率: ${(d.value * 100).toFixed(2)}%</div>
        `).style('opacity', 1)
          .style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      }
    })
  
  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(8))
  
  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y).tickFormat(d3.format('.0%')))
  
  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.3)
    .call(d3.axisLeft(y).tickSize(-width).tickFormat(''))
}

function renderLongShortChart() {
  const container = longShortChart.value
  if (!container || !result.value?.long_short_return) return
  
  const { svg, g, width, height } = setupChart(container)
  const tooltip = addTooltip(svg)
  
  const ls = result.value.long_short_return
  const parseDate = d3.timeParse('%Y-%m-%d')
  const data = (ls.cumulative_returns || []).map(r => ({
    date: parseDate(r.trade_date),
    cum: r.cumulative_return
  })).filter(d => d.date)
  
  const dailyData = (ls.returns || []).map(r => ({
    date: parseDate(r.trade_date),
    ret: r.return
  })).filter(d => d.date)
  
  if (data.length === 0) return
  
  const x = d3.scaleTime()
    .domain(d3.extent(data, d => d.date))
    .range([0, width])
  
  const [minC, maxC] = d3.extent(data, d => d.cum)
  const pad = Math.max(0.01, (maxC - minC) * 0.1)
  
  const y = d3.scaleLinear()
    .domain([minC - pad, maxC + pad])
    .range([height, 0])
  
  const retMap = {}
  dailyData.forEach(d => retMap[d.date.getTime()] = d.ret)
  
  const line = d3.line()
    .x(d => x(d.date))
    .y(d => y(d.cum))
    .curve(d3.curveMonotoneX)
  
  g.append('path')
    .datum(data)
    .attr('fill', 'none')
    .attr('stroke', d => ls.cumulative_return >= 0 ? '#67c23a' : '#f56c6c')
    .attr('stroke-width', 2.5)
    .attr('d', line)
  
  g.selectAll('.ls-dot')
    .data(data)
    .enter()
    .append('circle')
    .attr('class', 'ls-dot')
    .attr('cx', d => x(d.date))
    .attr('cy', d => y(d.cum))
    .attr('r', 2)
    .attr('fill', d => retMap[d.date.getTime()] >= 0 ? '#67c23a' : '#f56c6c')
    .attr('opacity', 0.7)
    .on('mouseover', function(event, d) {
      const daily = retMap[d.date.getTime()]
      tooltip.html(`
        <div>日期: ${d.trade_date}</div>
        <div>累计收益: ${(d.cum * 100).toFixed(2)}%</div>
        ${daily !== undefined ? `<div>当日收益: ${(daily * 100).toFixed(3)}%</div>` : ''}
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 12) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', function() {
      tooltip.style('opacity', 0)
    })
  
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(0)).attr('y2', y(0))
    .attr('stroke', '#909399')
    .attr('stroke-dasharray', '3,3')
  
  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(10))
  
  g.append('g')
    .attr('class', 'axis')
    .call(d3.axisLeft(y).tickFormat(d3.format('.1%')))
  
  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.3)
    .call(d3.axisLeft(y).tickSize(-width).tickFormat(''))
}

defineExpose({ visible })
</script>

<style scoped>
.grid-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 1200px) {
  .grid-container {
    grid-template-columns: 1fr;
  }
}
</style>
