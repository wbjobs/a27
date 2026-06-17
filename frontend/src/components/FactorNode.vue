<template>
  <div
    class="operator-node"
    :style="{ left: node.x + 'px', top: node.y + 'px' }"
    @mousedown.left="onNodeMouseDown"
    @click.stop="$emit('select')"
  >
    <div class="node-header" :class="categoryClass">
      <span>{{ node.name.split(' ')[0] }}</span>
      <div style="display: flex; gap: 4px;">
        <el-icon
          :size="14"
          :style="{ cursor: 'pointer', color: isOutput ? '#fde047' : 'rgba(255,255,255,0.7)' }"
          @click.stop="$emit('set-output')"
          title="设为输出节点"
        ><Star /></el-icon>
        <el-icon
          :size="14"
          style="cursor: pointer; color: rgba(255,255,255,0.7);"
          @click.stop="$emit('remove')"
          title="删除"
        ><Close /></el-icon>
      </div>
    </div>

    <div class="node-body">
      <div
        v-for="param in operator?.params || []"
        :key="param.id"
        class="node-param"
      >
        <label>{{ param.name }}</label>
        <el-input-number
          v-if="param.type === 'int' || param.type === 'float'"
          :model-value="node.params[param.id]"
          @update:model-value="(v) => updateParam(param.id, v)"
          :min="param.min"
          :max="param.max"
          :step="param.type === 'float' ? 0.1 : 1"
          size="small"
          controls-position="right"
        />
        <el-select
          v-else-if="param.type === 'select'"
          :model-value="node.params[param.id]"
          @update:model-value="(v) => updateParam(param.id, v)"
          size="small"
        >
          <el-option
            v-for="opt in param.options"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-switch
          v-else-if="param.type === 'boolean'"
          :model-value="node.params[param.id]"
          @update:model-value="(v) => updateParam(param.id, v)"
        />
      </div>
      <div v-if="!operator?.params?.length" class="text-muted">
        无参数配置
      </div>
    </div>

    <div
      v-for="(inp, idx) in operator?.inputs || []"
      :key="'in-' + inp.id"
      class="port port-input"
      :class="{ 'port-connected': isInputConnected(inp.id) }"
      :style="{ top: getInputTop(idx) + 'px' }"
      @mousedown.stop.prevent
      @mouseup.stop="onInputDrop(inp.id)"
      :title="inp.name"
    ></div>
    <div
      v-for="(inp, idx) in operator?.inputs || []"
      :key="'in-label-' + inp.id"
      class="port-label"
      :style="{ top: getInputTop(idx) - 6 + 'px' }"
    >{{ inp.name }}</div>

    <div
      v-for="(out, idx) in operator?.outputs || []"
      :key="'out-' + out.id"
      class="port port-output"
      :class="{ 'port-connected': isOutputConnected() }"
      :style="{ top: getOutputTop(idx) + 'px' }"
      @mousedown.stop="onOutputDragStart(out.id, $event)"
      :title="out.name"
    ></div>
    <div
      v-for="(out, idx) in operator?.outputs || []"
      :key="'out-label-' + out.id"
      class="port-label"
      :style="{ top: getOutputTop(idx) - 6 + 'px', textAlign: 'right' }"
    >{{ out.name }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Star, Close } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'

const props = defineProps({
  node: { type: Object, required: true }
})

const emit = defineEmits(['select', 'remove', 'set-output', 'move', 'port-drag-start', 'port-drop'])

const workflowStore = useWorkflowStore()

const operator = computed(() =>
  workflowStore.getOperatorById(props.node.operator_id)
)

const isOutput = computed(() =>
  workflowStore.outputNodeId === props.node.id
)

const categoryMap = {
  '趋势指标': 'node-category-trend',
  '动量指标': 'node-category-momentum',
  '波动率指标': 'node-category-volatility',
  '超买超卖指标': 'node-category-overbought',
  '成交量指标': 'node-category-volume',
  '基础指标': 'node-category-basic',
  '组合运算': 'node-category-combine',
  '标准化': 'node-category-normalize'
}

const categoryClass = computed(() =>
  categoryMap[props.node.category] || 'node-category-basic'
)

function updateParam(paramId, value) {
  workflowStore.updateNodeParam(props.node.id, paramId, value)
}

function onNodeMouseDown(e) {
  if (e.button !== 0) return
  emit('move', props.node.id, e)
}

function isInputConnected(inputId) {
  return workflowStore.edges.some(
    e => e.target === props.node.id && e.target_input === inputId
  )
}

function isOutputConnected() {
  return workflowStore.edges.some(e => e.source === props.node.id)
}

const HEADER_H = 40
const BODY_PAD = 12
const PARAM_H = 36
const BOTTOM_PAD = 10

function nodeHeight() {
  const nParams = operator.value?.params?.length || 0
  return HEADER_H + BODY_PAD * 2 + PARAM_H * nParams + BOTTOM_PAD
}

function getInputTop(idx) {
  const nInputs = operator.value?.inputs?.length || 1
  const h = nodeHeight()
  const spacing = (h - HEADER_H) / (nInputs + 1)
  return HEADER_H - 7 + spacing * (idx + 1)
}

function getOutputTop(idx) {
  const nOutputs = operator.value?.outputs?.length || 1
  const h = nodeHeight()
  const spacing = (h - HEADER_H) / (nOutputs + 1)
  return HEADER_H - 7 + spacing * (idx + 1)
}

function onOutputDragStart(outputId, e) {
  emit('port-drag-start', {
    nodeId: props.node.id,
    outputId
  })
}

function onInputDrop(inputId) {
  emit('port-drop', {
    nodeId: props.node.id,
    inputId
  })
}
</script>
