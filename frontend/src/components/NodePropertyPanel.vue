<template>
  <div>
    <div class="section-title">节点属性</div>
    
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="节点ID">{{ node?.id }}</el-descriptions-item>
      <el-descriptions-item label="算子">{{ node?.name }}</el-descriptions-item>
      <el-descriptions-item label="类别">{{ node?.category }}</el-descriptions-item>
      <el-descriptions-item label="是否输出">
        <el-tag :type="isOutput ? 'success' : 'info'" size="small">
          {{ isOutput ? '是' : '否' }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>

    <div v-if="operator" class="mt-md">
      <div class="sub-title">算子描述</div>
      <div class="text-muted" style="line-height: 1.6;">{{ operator.description }}</div>
    </div>

    <div v-if="operator?.params?.length" class="mt-md">
      <div class="sub-title">参数配置</div>
      <el-form label-position="top" size="default">
        <el-form-item
          v-for="param in operator.params"
          :key="param.id"
          :label="param.name"
        >
          <el-input-number
            v-if="param.type === 'int'"
            v-model="localParams[param.id]"
            :min="param.min"
            :max="param.max"
            step="1"
            style="width: 100%;"
            @change="(v) => updateParam(param.id, v)"
          />
          <el-input-number
            v-else-if="param.type === 'float'"
            v-model="localParams[param.id]"
            :min="param.min"
            :max="param.max"
            step="0.1"
            :precision="2"
            style="width: 100%;"
            @change="(v) => updateParam(param.id, v)"
          />
          <el-select
            v-else-if="param.type === 'select'"
            v-model="localParams[param.id]"
            style="width: 100%;"
            @change="(v) => updateParam(param.id, v)"
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
            v-model="localParams[param.id]"
            @change="(v) => updateParam(param.id, v)"
          />
        </el-form-item>
      </el-form>
    </div>

    <div v-if="operator?.inputs?.length" class="mt-md">
      <div class="sub-title">输入连接</div>
      <div
        v-for="inp in operator.inputs"
        :key="inp.id"
        style="padding: 8px; margin-bottom: 6px; background: #f5f7fa; border-radius: 4px;"
      >
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>{{ inp.name }}</strong>
            <div class="text-muted" style="font-size: 11px;">类型: {{ inp.type }}</div>
          </div>
          <el-tag v-if="node.inputs[inp.id]" size="small" type="success">
            已连接
          </el-tag>
          <el-tag v-else size="small" type="info">
            未连接
          </el-tag>
        </div>
        <div v-if="node.inputs[inp.id]" class="text-muted" style="font-size: 11px; margin-top: 4px;">
          来自: {{ node.inputs[inp.id] }}
        </div>
      </div>
    </div>

    <div v-if="operator?.outputs?.length" class="mt-md">
      <div class="sub-title">输出端口</div>
      <div
        v-for="out in operator.outputs"
        :key="out.id"
        style="padding: 8px; margin-bottom: 6px; background: #f5f7fa; border-radius: 4px;"
      >
        <strong>{{ out.name }}</strong>
        <div class="text-muted" style="font-size: 11px;">类型: {{ out.type }}</div>
      </div>
    </div>

    <div class="mt-md flex gap-sm">
      <el-button size="small" @click="$emit('select', null)">取消选中</el-button>
      <el-button
        size="small"
        :type="isOutput ? 'info' : 'success'"
        @click="setOutput"
      >
        {{ isOutput ? '取消输出' : '设为输出' }}
      </el-button>
      <el-button size="small" type="danger" @click="removeNode">
        删除节点
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useWorkflowStore } from '../stores/workflow'

const workflowStore = useWorkflowStore()

const node = computed(() => workflowStore.selectedNode)
const operator = computed(() =>
  node.value ? workflowStore.getOperatorById(node.value.operator_id) : null
)
const isOutput = computed(() =>
  workflowStore.outputNodeId === node.value?.id
)

const localParams = reactive({})

watch(() => node.value?.params, (params) => {
  if (params) {
    Object.keys(params).forEach(k => localParams[k] = params[k])
  }
}, { immediate: true, deep: true })

function updateParam(paramId, value) {
  if (node.value) {
    workflowStore.updateNodeParam(node.value.id, paramId, value)
  }
}

function setOutput() {
  if (node.value) {
    if (isOutput.value) {
      workflowStore.outputNodeId = null
    } else {
      workflowStore.setOutputNode(node.value.id)
    }
  }
}

function removeNode() {
  if (node.value) {
    workflowStore.removeNode(node.value.id)
  }
}
</script>
