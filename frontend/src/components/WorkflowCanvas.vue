<template>
  <div
    class="workflow-canvas flex-1"
    ref="canvasRef"
    @drop="onDrop"
    @dragover.prevent
    @click="onCanvasClick"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @wheel="onWheel"
    style="position: relative;"
  >
    <div
      :style="{
        transform: `translate(${workflowStore.pan.x}px, ${workflowStore.pan.y}px) scale(${workflowStore.scale})`,
        transformOrigin: '0 0',
        position: 'absolute',
        inset: 0
      }"
    >
      <svg
        style="position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none;"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#409eff" />
          </marker>
        </defs>

        <path
          v-for="edge in workflowStore.edges"
          :key="edge.id"
          :d="computeEdgePath(edge)"
          class="edge-path"
          :class="{ 'selected': workflowStore.selectedEdgeId === edge.id }"
          style="pointer-events: stroke;"
          :marker-end="workflowStore.selectedEdgeId === edge.id ? 'url(#arrowhead)' : ''"
          @click.stop="selectEdge(edge.id)"
          @dblclick.stop="removeEdge(edge.id)"
        />

        <path
          v-if="workflowStore.tempEdge"
          :d="computeTempEdgePath()"
          class="edge-temp"
        />
      </svg>

      <FactorNode
        v-for="node in workflowStore.nodes"
        :key="node.id"
        :node="node"
        :class="{ 'selected': workflowStore.selectedNodeId === node.id, 'output-node': workflowStore.outputNodeId === node.id }"
        @select="workflowStore.selectNode(node.id)"
        @remove="workflowStore.removeNode(node.id)"
        @set-output="workflowStore.setOutputNode(node.id)"
        @move="handleNodeMove"
        @port-drag-start="handlePortDragStart"
        @port-drop="handlePortDrop"
      />
    </div>

    <div style="position: absolute; bottom: 16px; right: 16px; display: flex; gap: 8px;">
      <el-button-group>
        <el-button size="small" @click="zoom(-0.1)" :icon="ZoomOut" />
        <el-button size="small" @click="resetView">100%</el-button>
        <el-button size="small" @click="zoom(0.1)" :icon="ZoomIn" />
      </el-button-group>
    </div>

    <div style="position: absolute; top: 12px; left: 12px;" class="text-muted">
      节点: {{ workflowStore.nodes.length }} | 连线: {{ workflowStore.edges.length }} 
      <span v-if="workflowStore.outputNodeId" style="color: var(--success-color);">
        | 输出: {{ workflowStore.getNodeById(workflowStore.outputNodeId)?.name }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'
import FactorNode from './FactorNode.vue'

const workflowStore = useWorkflowStore()
const canvasRef = ref(null)

const draggingNode = ref(null)
const dragOffset = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const activeTargetPort = ref(null)

function onDrop(e) {
  e.preventDefault()
  const opId = e.dataTransfer.getData('operatorId')
  if (!opId || !canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const x = (e.clientX - rect.left - workflowStore.pan.x) / workflowStore.scale
  const y = (e.clientY - rect.top - workflowStore.pan.y) / workflowStore.scale

  workflowStore.addNode(opId, x - 90, y - 30)
}

function onCanvasClick(e) {
  if (e.target === canvasRef.value || e.target.classList.contains('workflow-canvas')) {
    workflowStore.clearSelection()
    workflowStore.cancelDraggingEdge()
  }
}

function selectEdge(id) {
  workflowStore.selectEdge(id)
}

function removeEdge(id) {
  workflowStore.removeEdge(id)
}

function onMouseMove(e) {
  if (draggingNode.value && canvasRef.value) {
    const rect = canvasRef.value.getBoundingClientRect()
    const x = (e.clientX - rect.left - dragOffset.value.x - workflowStore.pan.x) / workflowStore.scale
    const y = (e.clientY - rect.top - dragOffset.value.y - workflowStore.pan.y) / workflowStore.scale
    workflowStore.updateNodePosition(draggingNode.value, x, y)
  }

  if (workflowStore.tempEdge) {
    const rect = canvasRef.value.getBoundingClientRect()
    const x = (e.clientX - rect.left - workflowStore.pan.x) / workflowStore.scale
    const y = (e.clientY - rect.top - workflowStore.pan.y) / workflowStore.scale
    workflowStore.updateTempEdge(x, y)
  }

  if (isPanning.value && canvasRef.value) {
    const dx = e.clientX - panStart.value.x
    const dy = e.clientY - panStart.value.y
    workflowStore.setPan(workflowStore.pan.x + dx, workflowStore.pan.y + dy)
    panStart.value = { x: e.clientX, y: e.clientY }
  }
}

function onMouseUp(e) {
  if (draggingNode.value) {
    draggingNode.value = null
  }
  if (workflowStore.tempEdge) {
    workflowStore.cancelDraggingEdge()
  }
  if (isPanning.value) {
    isPanning.value = false
  }
}

function onWheel(e) {
  e.preventDefault()
  const delta = -e.deltaY * 0.001
  zoom(delta)
}

function zoom(delta) {
  workflowStore.setScale(workflowStore.scale + delta)
}

function resetView() {
  workflowStore.setPan(0, 0)
  workflowStore.setScale(1)
}

function handleNodeMove(nodeId, event) {
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  draggingNode.value = nodeId
  const node = workflowStore.getNodeById(nodeId)
  if (node) {
    dragOffset.value = {
      x: event.clientX - rect.left - (node.x + workflowStore.pan.x) * workflowStore.scale,
      y: event.clientY - rect.top - (node.y + workflowStore.pan.y) * workflowStore.scale
    }
  }
}

function handlePortDragStart(payload) {
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const node = workflowStore.getNodeById(payload.nodeId)
  const operator = workflowStore.getOperatorById(node?.operator_id)
  const portPos = getPortPosition(node, operator, payload.outputId, 'output')
  const startX = (portPos.x - workflowStore.pan.x) / workflowStore.scale
  const startY = (portPos.y - workflowStore.pan.y) / workflowStore.scale
  workflowStore.startDraggingEdge(payload.nodeId, payload.outputId, startX, startY)
}

function handlePortDrop(payload) {
  workflowStore.finishDraggingEdge(payload.nodeId, payload.inputId)
}

function getNodeHeight(node) {
  const operator = workflowStore.getOperatorById(node.operator_id)
  if (!operator) return 100
  return 50 + (operator.params?.length || 0) * 36 + 30
}

function getPortPosition(node, operator, portId, type) {
  const width = 184
  const height = getNodeHeight(node)
  if (type === 'output') {
    const outputs = operator?.outputs || []
    const idx = Math.max(0, outputs.findIndex(o => o.id === portId))
    const spacing = (height - 40) / Math.max(1, outputs.length + 1)
    return {
      x: node.x + width,
      y: node.y + 40 + spacing * (idx + 1)
    }
  } else {
    const inputs = operator?.inputs || []
    const idx = Math.max(0, inputs.findIndex(i => i.id === portId))
    const spacing = (height - 40) / Math.max(1, inputs.length + 1)
    return {
      x: node.x,
      y: node.y + 40 + spacing * (idx + 1)
    }
  }
}

function computeEdgePath(edge) {
  const srcNode = workflowStore.getNodeById(edge.source)
  const tgtNode = workflowStore.getNodeById(edge.target)
  if (!srcNode || !tgtNode) return ''

  const srcOp = workflowStore.getOperatorById(srcNode.operator_id)
  const tgtOp = workflowStore.getOperatorById(tgtNode.operator_id)

  const src = getPortPosition(srcNode, srcOp, (srcOp?.outputs?.[0]?.id || 'output'), 'output')
  const tgt = getPortPosition(tgtNode, tgtOp, edge.target_input, 'input')

  const dx = Math.max(40, Math.abs(tgt.x - src.x) / 2)
  return `M ${src.x} ${src.y} C ${src.x + dx} ${src.y}, ${tgt.x - dx} ${tgt.y}, ${tgt.x} ${tgt.y}`
}

function computeTempEdgePath() {
  const t = workflowStore.tempEdge
  if (!t) return ''
  const dx = Math.max(40, Math.abs(t.x2 - t.x1) / 2)
  return `M ${t.x1} ${t.y1} C ${t.x1 + dx} ${t.y1}, ${t.x2 - dx} ${t.y2}, ${t.x2} ${t.y2}`
}
</script>
