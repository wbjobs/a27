<template>
  <div ref="chartContainer" class="chart-container" style="width: 100%; height: 100%; min-height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  monte_carlo_points: {
    type: Array,
    default: () => []
  },
  efficient_frontier: {
    type: Array,
    default: () => []
  },
  optimal_point: {
    type: Object,
    default: null
  }
})

const chartContainer = ref(null)
let svg = null
let g = null
let tooltip = null
let width = 0
let height = 0
let xScale = null
let yScale = null
let colorScale = null
let zoom = null

const margin = { top: 30, right: 80, bottom: 60, left: 70 }

function setupChart() {
  const container = chartContainer.value
  if (!container) return

  d3.select(container).selectAll('*').remove()

  const rect = container.getBoundingClientRect()
  width = rect.width - margin.left - margin.right
  height = rect.height - margin.top - margin.bottom

  svg = d3.select(container)
    .append('svg')
    .attr('width', rect.width)
    .attr('height', rect.height)

  g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  tooltip = d3.select('body').append('div')
    .attr('class', 'chart-tooltip')
    .style('opacity', 0)
    .style('position', 'absolute')
    .style('background', 'rgba(0, 0, 0, 0.85)')
    .style('color', '#fff')
    .style('padding', '10px 14px')
    .style('border-radius', '6px')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('z-index', 1000)
    .style('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.3)')

  return { svg, g, width, height }
}

function createScales() {
  const allPoints = [
    ...props.monte_carlo_points,
    ...props.efficient_frontier,
    props.optimal_point
  ].filter(Boolean)

  if (allPoints.length === 0) return

  const xExtent = d3.extent(allPoints, d => d.expected_volatility)
  const yExtent = d3.extent(allPoints, d => d.expected_return)
  const sharpeExtent = d3.extent(props.monte_carlo_points, d => d.sharpe_ratio)

  const xPad = (xExtent[1] - xExtent[0]) * 0.08 || 0.01
  const yPad = (yExtent[1] - yExtent[0]) * 0.08 || 0.01

  xScale = d3.scaleLinear()
    .domain([Math.max(0, xExtent[0] - xPad), xExtent[1] + xPad])
    .range([0, width])

  yScale = d3.scaleLinear()
    .domain([yExtent[0] - yPad, yExtent[1] + yPad])
    .range([height, 0])

  colorScale = d3.scaleSequential()
    .domain(sharpeExtent)
    .interpolator(d3.interpolateViridis)
}

function addAxes() {
  g.append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale)
      .ticks(8)
      .tickFormat(d3.format('.2%'))
    )
    .style('font-size', '11px')

  g.append('text')
    .attr('class', 'x-label')
    .attr('x', width / 2)
    .attr('y', height + 45)
    .attr('text-anchor', 'middle')
    .attr('fill', '#606266')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .text('预期波动率 (风险)')

  g.append('g')
    .attr('class', 'y-axis')
    .call(d3.axisLeft(yScale)
      .ticks(8)
      .tickFormat(d3.format('.2%'))
    )
    .style('font-size', '11px')

  g.append('text')
    .attr('class', 'y-label')
    .attr('transform', 'rotate(-90)')
    .attr('x', -height / 2)
    .attr('y', -50)
    .attr('text-anchor', 'middle')
    .attr('fill', '#606266')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .text('预期收益率')
}

function addGrid() {
  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.25)
    .call(d3.axisLeft(yScale)
      .tickSize(-width)
      .tickFormat('')
    )

  g.append('g')
    .attr('class', 'grid')
    .attr('opacity', 0.25)
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale)
      .tickSize(-height)
      .tickFormat('')
    )
}

function formatWeights(weights) {
  if (!weights) return ''
  return Object.entries(weights)
    .map(([k, v]) => `${k}: ${(v * 100).toFixed(2)}%`)
    .join('<br/>')
}

function renderMonteCarloPoints() {
  if (!props.monte_carlo_points?.length) return

  g.selectAll('.monte-carlo-point')
    .data(props.monte_carlo_points)
    .enter()
    .append('circle')
    .attr('class', 'monte-carlo-point')
    .attr('cx', d => xScale(d.expected_volatility))
    .attr('cy', d => yScale(d.expected_return))
    .attr('r', 3)
    .attr('fill', d => colorScale(d.sharpe_ratio))
    .attr('opacity', 0.7)
    .attr('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 5)
        .attr('opacity', 1)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)

      tooltip.html(`
        <div style="margin-bottom: 6px; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 4px;">
          蒙特卡洛模拟点
        </div>
        <div style="margin-bottom: 4px;">预期收益率: <span style="color: #67c23a; font-weight: 500;">${(d.expected_return * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">预期波动率: <span style="color: #e6a23c; font-weight: 500;">${(d.expected_volatility * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">夏普比率: <span style="color: #409eff; font-weight: 500;">${d.sharpe_ratio.toFixed(3)}</span></div>
        ${d.weights ? `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.2);"><strong>权重:</strong><br/>${formatWeights(d.weights)}</div>` : ''}
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 10) + 'px')
    })
    .on('mouseout', function() {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 3)
        .attr('opacity', 0.7)
        .attr('stroke', 'none')
        .attr('stroke-width', 0)

      tooltip.style('opacity', 0)
    })
}

function renderEfficientFrontier() {
  if (!props.efficient_frontier?.length) return

  const sortedFrontier = [...props.efficient_frontier].sort(
    (a, b) => a.expected_volatility - b.expected_volatility
  )

  const line = d3.line()
    .x(d => xScale(d.expected_volatility))
    .y(d => yScale(d.expected_return))
    .curve(d3.curveCatmullRom.alpha(0.5))

  g.append('path')
    .datum(sortedFrontier)
    .attr('class', 'efficient-frontier-line')
    .attr('fill', 'none')
    .attr('stroke', '#f56c6c')
    .attr('stroke-width', 2.5)
    .attr('d', line)

  g.selectAll('.frontier-point')
    .data(sortedFrontier)
    .enter()
    .append('circle')
    .attr('class', 'frontier-point')
    .attr('cx', d => xScale(d.expected_volatility))
    .attr('cy', d => yScale(d.expected_return))
    .attr('r', 4)
    .attr('fill', '#f56c6c')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)
    .attr('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 6)

      tooltip.html(`
        <div style="margin-bottom: 6px; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 4px; color: #f56c6c;">
          有效前沿点
        </div>
        <div style="margin-bottom: 4px;">预期收益率: <span style="color: #67c23a; font-weight: 500;">${(d.expected_return * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">预期波动率: <span style="color: #e6a23c; font-weight: 500;">${(d.expected_volatility * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">夏普比率: <span style="color: #409eff; font-weight: 500;">${d.sharpe_ratio.toFixed(3)}</span></div>
        ${d.weights ? `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.2);"><strong>权重:</strong><br/>${formatWeights(d.weights)}</div>` : ''}
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 10) + 'px')
    })
    .on('mouseout', function() {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 4)

      tooltip.style('opacity', 0)
    })
}

function renderOptimalPoint() {
  if (!props.optimal_point) return

  const d = props.optimal_point

  g.append('circle')
    .attr('class', 'optimal-point-glow')
    .attr('cx', xScale(d.expected_volatility))
    .attr('cy', yScale(d.expected_return))
    .attr('r', 18)
    .attr('fill', '#ff9900')
    .attr('opacity', 0.2)

  g.append('circle')
    .attr('class', 'optimal-point')
    .attr('cx', xScale(d.expected_volatility))
    .attr('cy', yScale(d.expected_return))
    .attr('r', 9)
    .attr('fill', '#ff9900')
    .attr('stroke', '#fff')
    .attr('stroke-width', 2.5)
    .attr('cursor', 'pointer')
    .style('filter', 'drop-shadow(0 2px 6px rgba(255, 153, 0, 0.5))')
    .on('mouseover', function() {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 11)

      tooltip.html(`
        <div style="margin-bottom: 6px; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 4px; color: #ff9900;">
          ★ 最优投资组合
        </div>
        <div style="margin-bottom: 4px;">预期收益率: <span style="color: #67c23a; font-weight: 500;">${(d.expected_return * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">预期波动率: <span style="color: #e6a23c; font-weight: 500;">${(d.expected_volatility * 100).toFixed(2)}%</span></div>
        <div style="margin-bottom: 4px;">夏普比率: <span style="color: #409eff; font-weight: 500;">${d.sharpe_ratio.toFixed(3)}</span></div>
        ${d.weights ? `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.2);"><strong>权重:</strong><br/>${formatWeights(d.weights)}</div>` : ''}
      `).style('opacity', 1)
    })
    .on('mousemove', function(event) {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 10) + 'px')
    })
    .on('mouseout', function() {
      d3.select(this)
        .transition()
        .duration(150)
        .attr('r', 9)

      tooltip.style('opacity', 0)
    })
}

function addLegend() {
  const legend = g.append('g')
    .attr('class', 'legend')
    .attr('transform', `translate(${width + 15}, 0)`)

  const legendItems = [
    { label: '蒙特卡洛模拟', color: 'url(#viridis-gradient)', type: 'gradient' },
    { label: '有效前沿', color: '#f56c6c', type: 'line' },
    { label: '最优组合', color: '#ff9900', type: 'circle' }
  ]

  const defs = svg.append('defs')
  const gradient = defs.append('linearGradient')
    .attr('id', 'viridis-gradient')
    .attr('x1', '0%')
    .attr('y1', '0%')
    .attr('x2', '100%')
    .attr('y2', '0%')

  for (let i = 0; i <= 10; i++) {
    gradient.append('stop')
      .attr('offset', `${i * 10}%`)
      .attr('stop-color', colorScale ? colorScale(colorScale.domain()[0] + (colorScale.domain()[1] - colorScale.domain()[0]) * i / 10) : '#440154')
  }

  legend.append('rect')
    .attr('width', 145)
    .attr('height', 110)
    .attr('fill', '#fff')
    .attr('stroke', '#e4e7ed')
    .attr('stroke-width', 1)
    .attr('rx', 6)
    .attr('ry', 6)
    .style('filter', 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08))')

  legend.append('text')
    .attr('x', 12)
    .attr('y', 24)
    .attr('font-size', '12px')
    .attr('font-weight', '600')
    .attr('fill', '#303133')
    .text('图例')

  legendItems.forEach((item, i) => {
    const y = 50 + i * 24

    if (item.type === 'gradient') {
      legend.append('rect')
        .attr('x', 12)
        .attr('y', y - 8)
        .attr('width', 18)
        .attr('height', 12)
        .attr('fill', item.color)
        .attr('rx', 2)
    } else if (item.type === 'line') {
      legend.append('line')
        .attr('x1', 12)
        .attr('x2', 30)
        .attr('y1', y - 2)
        .attr('y2', y - 2)
        .attr('stroke', item.color)
        .attr('stroke-width', 2.5)
    } else if (item.type === 'circle') {
      legend.append('circle')
        .attr('cx', 21)
        .attr('cy', y - 2)
        .attr('r', 6)
        .attr('fill', item.color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
    }

    legend.append('text')
      .attr('x', 40)
      .attr('y', y + 2)
      .attr('font-size', '11px')
      .attr('fill', '#606266')
      .text(item.label)
  })

  if (props.monte_carlo_points?.length) {
    const sharpeMin = d3.min(props.monte_carlo_points, d => d.sharpe_ratio)
    const sharpeMax = d3.max(props.monte_carlo_points, d => d.sharpe_ratio)

    legend.append('text')
      .attr('x', 12)
      .attr('y', 102)
      .attr('font-size', '10px')
      .attr('fill', '#909399')
      .text(`夏普: ${sharpeMin.toFixed(2)} - ${sharpeMax.toFixed(2)}`)
  }
}

function addZoom() {
  zoom = d3.zoom()
    .scaleExtent([0.5, 5])
    .on('zoom', (event) => {
      const newX = event.transform.rescaleX(xScale)
      const newY = event.transform.rescaleY(yScale)

      g.select('.x-axis').call(d3.axisBottom(newX).ticks(8).tickFormat(d3.format('.2%')))
      g.select('.y-axis').call(d3.axisLeft(newY).ticks(8).tickFormat(d3.format('.2%')))

      g.selectAll('.monte-carlo-point')
        .attr('cx', d => newX(d.expected_volatility))
        .attr('cy', d => newY(d.expected_return))

      g.select('.efficient-frontier-line')
        .attr('d', d3.line()
          .x(d => newX(d.expected_volatility))
          .y(d => newY(d.expected_return))
          .curve(d3.curveCatmullRom.alpha(0.5))
        )

      g.selectAll('.frontier-point')
        .attr('cx', d => newX(d.expected_volatility))
        .attr('cy', d => newY(d.expected_return))

      if (props.optimal_point) {
        g.selectAll('.optimal-point, .optimal-point-glow')
          .attr('cx', newX(props.optimal_point.expected_volatility))
          .attr('cy', newY(props.optimal_point.expected_return))
      }

      g.select('.grid').remove()
      const gridG = g.insert('g', ':first-child')
        .attr('class', 'grid')
        .attr('opacity', 0.25)

      gridG.append('g')
        .call(d3.axisLeft(newY).tickSize(-width).tickFormat(''))

      gridG.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(newX).tickSize(-height).tickFormat(''))
    })

  svg.call(zoom)

  svg.on('dblclick.zoom', null)
}

function render() {
  const hasData = props.monte_carlo_points?.length > 0 ||
                  props.efficient_frontier?.length > 0 ||
                  props.optimal_point

  if (!hasData) return

  setupChart()
  createScales()
  addGrid()
  renderMonteCarloPoints()
  renderEfficientFrontier()
  renderOptimalPoint()
  addAxes()
  addLegend()
  addZoom()
}

let resizeObserver = null

function handleResize() {
  nextTick(() => {
    render()
  })
}

onMounted(() => {
  render()

  resizeObserver = new ResizeObserver(handleResize)
  if (chartContainer.value) {
    resizeObserver.observe(chartContainer.value)
  }
})

onUnmounted(() => {
  if (tooltip) {
    tooltip.remove()
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

watch(
  () => [props.monte_carlo_points, props.efficient_frontier, props.optimal_point],
  () => {
    nextTick(() => render())
  },
  { deep: true }
)
</script>

<style scoped>
.chart-container :deep(.axis path),
.chart-container :deep(.axis line) {
  stroke: #c0c4cc;
}

.chart-container :deep(.axis text) {
  fill: #606266;
}

.chart-container :deep(.grid line) {
  stroke: #c0c4cc;
  stroke-dasharray: 2, 2;
}

.chart-container :deep(.grid path) {
  stroke-width: 0;
}
</style>
