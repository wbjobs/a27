<template>
  <div ref="container" class="shap-force-plot">
    <svg ref="svg" :width="svgWidth" :height="svgHeight"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data: {
    type: Object,
    required: true,
    validator: (val) => {
      return val && typeof val.base_value === 'number' && Array.isArray(val.features)
    }
  },
  predicted: {
    type: Number,
    required: true
  }
})

const container = ref(null)
const svg = ref(null)
const svgWidth = ref(0)
const svgHeight = ref(180)

let tooltip = null
let resizeObserver = null

const margin = { top: 30, right: 80, bottom: 40, left: 80 }

function setupTooltip() {
  if (tooltip) {
    d3.select(tooltip).remove()
  }
  tooltip = d3.select('body').append('div')
    .attr('class', 'chart-tooltip')
    .style('opacity', 0)
}

function getColor(contribution) {
  return contribution >= 0 ? '#f56c6c' : '#409eff'
}

function formatValue(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  if (Math.abs(v) >= 1000 || Math.abs(v) < 0.001) {
    return d3.format('.3e')(v)
  }
  return d3.format('.4f')(v)
}

function render() {
  if (!svg.value || !props.data || !props.data.features) return

  const node = svg.value
  d3.select(node).selectAll('*').remove()

  const features = [...props.data.features].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
  const baseValue = props.data.base_value
  const predicted = props.predicted

  const width = svgWidth.value - margin.left - margin.right
  const height = svgHeight.value - margin.top - margin.bottom

  const minVal = Math.min(baseValue, predicted, ...features.map(f => baseValue + f.shap_value))
  const maxVal = Math.max(baseValue, predicted, ...features.map(f => baseValue + f.shap_value))
  const pad = (maxVal - minVal) * 0.1 || 0.01

  const x = d3.scaleLinear()
    .domain([minVal - pad, maxVal + pad])
    .range([0, width])

  const g = d3.select(node)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const totalAbsShap = d3.sum(features, d => Math.abs(d.shap_value))

  let currentPos = baseValue
  const positiveFeatures = features.filter(f => f.shap_value >= 0).sort((a, b) => b.shap_value - a.shap_value)
  const negativeFeatures = features.filter(f => f.shap_value < 0).sort((a, b) => a.shap_value - b.shap_value)

  const blockData = []

  positiveFeatures.forEach(f => {
    const start = currentPos
    const end = currentPos + f.shap_value
    blockData.push({
      ...f,
      start,
      end,
      contribution: f.shap_value,
      color: getColor(f.shap_value)
    })
    currentPos = end
  })

  currentPos = baseValue
  negativeFeatures.forEach(f => {
    const end = currentPos
    const start = currentPos + f.shap_value
    blockData.push({
      ...f,
      start,
      end,
      contribution: f.shap_value,
      color: getColor(f.shap_value)
    })
    currentPos = start
  })

  g.append('line')
    .attr('x1', x(minVal - pad))
    .attr('x2', x(maxVal + pad))
    .attr('y1', height / 2)
    .attr('y2', height / 2)
    .attr('stroke', '#e4e7ed')
    .attr('stroke-width', 3)

  const baseGroup = g.append('g')
  baseGroup.append('line')
    .attr('x1', x(baseValue))
    .attr('x2', x(baseValue))
    .attr('y1', height / 2 - 20)
    .attr('y2', height / 2 + 20)
    .attr('stroke', '#909399')
    .attr('stroke-width', 2)
  baseGroup.append('circle')
    .attr('cx', x(baseValue))
    .attr('cy', height / 2)
    .attr('r', 8)
    .attr('fill', '#fff')
    .attr('stroke', '#909399')
    .attr('stroke-width', 2)
  baseGroup.append('text')
    .attr('x', x(baseValue))
    .attr('y', height / 2 - 28)
    .attr('text-anchor', 'middle')
    .attr('fill', '#606266')
    .attr('font-size', '11px')
    .attr('font-weight', '500')
    .text('Base Value')
  baseGroup.append('text')
    .attr('x', x(baseValue))
    .attr('y', height / 2 + 38)
    .attr('text-anchor', 'middle')
    .attr('fill', '#303133')
    .attr('font-size', '12px')
    .attr('font-weight', '600')
    .text(formatValue(baseValue))

  const predGroup = g.append('g')
  predGroup.append('line')
    .attr('x1', x(predicted))
    .attr('x2', x(predicted))
    .attr('y1', height / 2 - 20)
    .attr('y2', height / 2 + 20)
    .attr('stroke', '#67c23a')
    .attr('stroke-width', 2)
  predGroup.append('circle')
    .attr('cx', x(predicted))
    .attr('cy', height / 2)
    .attr('r', 8)
    .attr('fill', '#fff')
    .attr('stroke', '#67c23a')
    .attr('stroke-width', 2)
  predGroup.append('text')
    .attr('x', x(predicted))
    .attr('y', height / 2 - 28)
    .attr('text-anchor', 'middle')
    .attr('fill', '#606266')
    .attr('font-size', '11px')
    .attr('font-weight', '500')
    .text('Predicted')
  predGroup.append('text')
    .attr('x', x(predicted))
    .attr('y', height / 2 + 38)
    .attr('text-anchor', 'middle')
    .attr('fill', '#67c23a')
    .attr('font-size', '12px')
    .attr('font-weight', '600')
    .text(formatValue(predicted))

  const defs = d3.select(node).append('defs')
  const gradientId = 'arrow-gradient-' + Date.now()
  const arrowGrad = defs.append('linearGradient')
    .attr('id', gradientId)
    .attr('x1', '0%').attr('y1', '0%')
    .attr('x2', '100%').attr('y2', '0%')
  arrowGrad.append('stop').attr('offset', '0%').attr('stop-color', '#909399')
  arrowGrad.append('stop').attr('offset', '100%').attr('stop-color', '#67c23a')

  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 8)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M 0,-5 L 10,0 L 0,5')
    .attr('fill', '#67c23a')

  if (Math.abs(x(predicted) - x(baseValue)) > 20) {
    g.append('line')
      .attr('x1', x(baseValue) + 12)
      .attr('x2', x(predicted) - 12)
      .attr('y1', height / 2 - 35)
      .attr('y2', height / 2 - 35)
      .attr('stroke', `url(#${gradientId})`)
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,3')
      .attr('marker-end', 'url(#arrowhead)')
  }

  const barHeight = Math.min(50, Math.max(20, height / Math.max(1, Math.ceil(features.length / 2))))
  const verticalGap = 4

  const posBlocks = blockData.filter(d => d.contribution >= 0)
  const negBlocks = blockData.filter(d => d.contribution < 0)

  posBlocks.forEach((d, i) => {
    const yOffset = -(barHeight + verticalGap) * (i + 1) + verticalGap / 2
    const xStart = x(Math.min(d.start, d.end))
    const xEnd = x(Math.max(d.start, d.end))
    const blockWidth = Math.max(2, xEnd - xStart)

    const blockGroup = g.append('g')
      .attr('cursor', 'pointer')

    blockGroup.append('rect')
      .attr('x', xStart)
      .attr('y', height / 2 + yOffset - barHeight / 2)
      .attr('width', blockWidth)
      .attr('height', barHeight)
      .attr('fill', d.color)
      .attr('opacity', 0.85)
      .attr('rx', 3)
      .on('mouseover', function(event) {
        d3.select(this).attr('opacity', 1).attr('stroke', '#303133').attr('stroke-width', 1)
        const pct = totalAbsShap > 0 ? Math.abs(d.contribution) / totalAbsShap * 100 : 0
        tooltip.html(`
          <div style="font-weight: 600; margin-bottom: 4px;">${d.name}</div>
          <div>特征值: ${formatValue(d.value)}</div>
          <div>SHAP 值: <span style="color: ${d.color}; font-weight: 500;">${formatValue(d.shap_value)}</span></div>
          <div>贡献方向: ${d.contribution >= 0 ? '正向 +' : '负向 '}${formatValue(d.contribution)}</div>
          <div>贡献占比: ${pct.toFixed(2)}%</div>
        `).style('opacity', 1)
      })
      .on('mousemove', function(event) {
        tooltip
          .style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      })
      .on('mouseout', function() {
        d3.select(this).attr('opacity', 0.85).attr('stroke', 'none').attr('stroke-width', 0)
        tooltip.style('opacity', 0)
      })

    if (blockWidth > 40) {
      blockGroup.append('text')
        .attr('x', xStart + blockWidth / 2)
        .attr('y', height / 2 + yOffset + 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(d.name.length > 8 ? d.name.substring(0, 8) + '...' : d.name)
    }

    blockGroup.append('line')
      .attr('x1', x(d.start))
      .attr('x2', x(d.start))
      .attr('y1', height / 2)
      .attr('y2', height / 2 + yOffset - barHeight / 2)
      .attr('stroke', d.color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.6)

    blockGroup.append('line')
      .attr('x1', x(d.end))
      .attr('x2', x(d.end))
      .attr('y1', height / 2)
      .attr('y2', height / 2 + yOffset - barHeight / 2)
      .attr('stroke', d.color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.6)
  })

  negBlocks.forEach((d, i) => {
    const yOffset = (barHeight + verticalGap) * (i + 1) - verticalGap / 2
    const xStart = x(Math.min(d.start, d.end))
    const xEnd = x(Math.max(d.start, d.end))
    const blockWidth = Math.max(2, xEnd - xStart)

    const blockGroup = g.append('g')
      .attr('cursor', 'pointer')

    blockGroup.append('rect')
      .attr('x', xStart)
      .attr('y', height / 2 + yOffset - barHeight / 2)
      .attr('width', blockWidth)
      .attr('height', barHeight)
      .attr('fill', d.color)
      .attr('opacity', 0.85)
      .attr('rx', 3)
      .on('mouseover', function(event) {
        d3.select(this).attr('opacity', 1).attr('stroke', '#303133').attr('stroke-width', 1)
        const pct = totalAbsShap > 0 ? Math.abs(d.contribution) / totalAbsShap * 100 : 0
        tooltip.html(`
          <div style="font-weight: 600; margin-bottom: 4px;">${d.name}</div>
          <div>特征值: ${formatValue(d.value)}</div>
          <div>SHAP 值: <span style="color: ${d.color}; font-weight: 500;">${formatValue(d.shap_value)}</span></div>
          <div>贡献方向: ${d.contribution >= 0 ? '正向 +' : '负向 '}${formatValue(d.contribution)}</div>
          <div>贡献占比: ${pct.toFixed(2)}%</div>
        `).style('opacity', 1)
      })
      .on('mousemove', function(event) {
        tooltip
          .style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      })
      .on('mouseout', function() {
        d3.select(this).attr('opacity', 0.85).attr('stroke', 'none').attr('stroke-width', 0)
        tooltip.style('opacity', 0)
      })

    if (blockWidth > 40) {
      blockGroup.append('text')
        .attr('x', xStart + blockWidth / 2)
        .attr('y', height / 2 + yOffset + 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(d.name.length > 8 ? d.name.substring(0, 8) + '...' : d.name)
    }

    blockGroup.append('line')
      .attr('x1', x(d.start))
      .attr('x2', x(d.start))
      .attr('y1', height / 2)
      .attr('y2', height / 2 + yOffset + barHeight / 2)
      .attr('stroke', d.color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.6)

    blockGroup.append('line')
      .attr('x1', x(d.end))
      .attr('x2', x(d.end))
      .attr('y1', height / 2)
      .attr('y2', height / 2 + yOffset + barHeight / 2)
      .attr('stroke', d.color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.6)
  })

  g.append('g')
    .attr('transform', `translate(0,${height - 10})`)
    .attr('class', 'axis')
    .call(d3.axisBottom(x).ticks(6).tickFormat(d => d3.format('.2f')(d)))
}

function updateSize() {
  if (!container.value) return
  const rect = container.value.getBoundingClientRect()
  svgWidth.value = rect.width
  const featureCount = props.data?.features?.length || 5
  const baseHeight = 180
  const additionalHeight = Math.max(0, featureCount - 4) * 25
  svgHeight.value = Math.min(400, baseHeight + additionalHeight)
}

function handleResize() {
  updateSize()
  nextTick(() => render())
}

watch([() => props.data, () => props.predicted], () => {
  updateSize()
  nextTick(() => render())
}, { deep: true })

onMounted(() => {
  setupTooltip()
  updateSize()
  nextTick(() => render())

  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container.value)
  }

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (tooltip) {
    d3.select(tooltip).remove()
    tooltip = null
  }
  if (resizeObserver && container.value) {
    resizeObserver.unobserve(container.value)
    resizeObserver = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.shap-force-plot {
  width: 100%;
  height: 100%;
  min-height: 180px;
  background: #fff;
  border-radius: 4px;
}
</style>
