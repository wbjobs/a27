<template>
  <div>
    <div class="section-title">算子面板</div>
    <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 12px;">
      拖拽算子到画布构建因子
    </div>

    <div v-for="(ops, cat) in sortedCategories" :key="cat" class="sidebar-section">
      <div class="sub-title flex items-center" style="cursor: pointer;" @click="toggleCategory(cat)">
        <el-icon :size="12" style="margin-right: 4px;">
          <component :is="expanded[cat] ? 'ArrowDown' : 'ArrowRight'" />
        </el-icon>
        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;" :style="{ background: categoryColors[cat] }"></span>
        {{ cat }}
        <span class="text-muted" style="margin-left: auto;">{{ ops.length }}</span>
      </div>
      <div v-show="expanded[cat]">
        <div
          v-for="op in ops"
          :key="op.id"
          class="operator-palette-item"
          draggable="true"
          @dragstart="onDragStart($event, op)"
        >
          <span class="operator-cat-badge" :style="{ background: categoryColors[cat] }"></span>
          <strong>{{ op.name.split(' ')[0] }}</strong>
          <div class="text-muted" style="margin-top: 4px; font-size: 10px;">
            {{ op.description }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { useWorkflowStore } from '../stores/workflow'

const workflowStore = useWorkflowStore()

const categoryColors = {
  '趋势指标': 'linear-gradient(135deg, #667eea, #764ba2)',
  '动量指标': 'linear-gradient(135deg, #f093fb, #f5576c)',
  '波动率指标': 'linear-gradient(135deg, #4facfe, #00f2fe)',
  '超买超卖指标': 'linear-gradient(135deg, #fa709a, #fee140)',
  '成交量指标': 'linear-gradient(135deg, #30cfd0, #330867)',
  '基础指标': 'linear-gradient(135deg, #a8edea, #fed6e3)',
  '组合运算': 'linear-gradient(135deg, #ffecd2, #fcb69f)',
  '标准化': 'linear-gradient(135deg, #84fab0, #8fd3f4)'
}

const expanded = ref({})

const sortedCategories = computed(() => {
  const byCat = workflowStore.operatorsByCategory || {}
  Object.keys(byCat).forEach(cat => {
    if (!(cat in expanded.value)) {
      expanded.value[cat] = true
    }
  })
  return byCat
})

function toggleCategory(cat) {
  expanded.value[cat] = !expanded.value[cat]
}

function onDragStart(e, op) {
  e.dataTransfer.setData('operatorId', op.id)
  e.dataTransfer.effectAllowed = 'copy'
}
</script>
