<template>
  <div>
    <div class="section-title">算子面板</div>
    <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 12px;">
      拖拽算子到画布构建因子
    </div>

    <el-input
      v-model="searchQuery"
      placeholder="搜索算子..."
      size="small"
      clearable
      style="margin-bottom: 12px;"
    />

    <div
      ref="scrollContainerRef"
      style="overflow-y: auto; max-height: calc(100vh - 200px);"
      @scroll="onScroll"
    >
      <div :style="{ height: totalHeight + 'px', position: 'relative' }">
        <div
          :style="{
            position: 'absolute',
            top: '0',
            left: '0',
            right: '0',
            transform: `translateY(${offsetY}px)`
          }"
        >
          <template v-for="item in visibleItems" :key="item.key">
            <div
              v-if="item.type === 'category'"
              class="sub-title flex items-center"
              style="cursor: pointer; padding: 8px 4px;"
              @click="toggleCategory(item.name)"
            >
              <el-icon :size="12" style="margin-right: 4px;">
                <component :is="expanded[item.name] ? 'ArrowDown' : 'ArrowRight'" />
              </el-icon>
              <span
                style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;"
                :style="{ background: categoryColors[item.name] }"
              ></span>
              {{ item.name }}
              <span class="text-muted" style="margin-left: auto;">{{ item.count }}</span>
            </div>
            <div
              v-else
              class="operator-palette-item"
              draggable="true"
              @dragstart="onDragStart($event, item.operator)"
            >
              <span
                class="operator-cat-badge"
                :style="{ background: categoryColors[item.category] }"
              ></span>
              <strong>{{ item.operator.name.split(' ')[0] }}</strong>
              <div class="text-muted" style="margin-top: 4px; font-size: 10px;">
                {{ item.operator.description }}
              </div>
              <el-tag
                v-if="item.operator.lookback > 0"
                size="small"
                type="warning"
                style="margin-top: 4px; font-size: 9px;"
              >回溯{{ item.operator.lookback }}期</el-tag>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
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
const searchQuery = ref('')
const scrollContainerRef = ref(null)
const scrollTop = ref(0)

const ITEM_HEIGHT = 52
const CATEGORY_HEIGHT = 36
const BUFFER = 5

const filteredItems = computed(() => {
  const byCat = workflowStore.operatorsByCategory || {}
  const query = searchQuery.value.toLowerCase().trim()
  const items = []

  const sortedCats = Object.keys(byCat).sort()
  for (const cat of sortedCats) {
    let ops = byCat[cat]
    if (query) {
      ops = ops.filter(op =>
        op.name.toLowerCase().includes(query) ||
        op.description.toLowerCase().includes(query) ||
        op.id.toLowerCase().includes(query)
      )
      if (ops.length === 0) continue
    }

    if (!(cat in expanded.value)) {
      expanded.value[cat] = true
    }

    items.push({
      type: 'category',
      name: cat,
      count: ops.length,
      height: CATEGORY_HEIGHT,
      key: `cat-${cat}`
    })

    if (expanded.value[cat]) {
      ops.forEach(op => {
        items.push({
          type: 'operator',
          operator: op,
          category: cat,
          height: ITEM_HEIGHT,
          key: `op-${op.id}`
        })
      })
    }
  }

  return items
})

const totalHeight = computed(() =>
  filteredItems.value.reduce((sum, item) => sum + item.height, 0)
)

const visibleItems = computed(() => {
  const items = filteredItems.value
  let currentY = 0
  let startIdx = 0
  let endIdx = items.length - 1

  for (let i = 0; i < items.length; i++) {
    if (currentY + items[i].height > scrollTop.value - BUFFER * ITEM_HEIGHT) {
      startIdx = i
      break
    }
    currentY += items[i].height
  }

  let visibleHeight = 0
  const containerH = scrollContainerRef.value?.clientHeight || 800
  for (let i = startIdx; i < items.length; i++) {
    visibleHeight += items[i].height
    if (visibleHeight > containerH + BUFFER * ITEM_HEIGHT * 2) {
      endIdx = i
      break
    }
  }

  return items.slice(startIdx, endIdx + 1)
})

const offsetY = computed(() => {
  const items = filteredItems.value
  let y = 0
  for (const item of items) {
    if (item === visibleItems.value[0]) break
    y += item.height
  }
  return y
})

function onScroll() {
  if (scrollContainerRef.value) {
    scrollTop.value = scrollContainerRef.value.scrollTop
  }
}

function toggleCategory(cat) {
  expanded.value[cat] = !expanded.value[cat]
}

function onDragStart(e, op) {
  e.dataTransfer.setData('operatorId', op.id)
  e.dataTransfer.effectAllowed = 'copy'
}
</script>
