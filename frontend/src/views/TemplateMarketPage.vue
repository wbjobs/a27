<template>
  <div class="page-container p-md">
    <div class="page-header">
      <h2 class="page-title">模板市场</h2>
      <el-button type="primary" :icon="Plus" @click="openPublishDialog">
        发布模板
      </el-button>
    </div>

    <el-card class="filter-card mt-md">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索模板名称或描述"
            :prefix-icon="Search"
            clearable
            @keyup.enter="fetchTemplates"
            @clear="fetchTemplates"
          />
        </el-col>
        <el-col :span="5">
          <el-select
            v-model="selectedCategory"
            placeholder="选择分类"
            clearable
            style="width: 100%;"
            @change="fetchTemplates"
            @clear="fetchTemplates"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select
            v-model="sortBy"
            placeholder="排序方式"
            style="width: 100%;"
            @change="fetchTemplates"
          >
            <el-option label="最新发布" value="latest" />
            <el-option label="最多点赞" value="most_liked" />
            <el-option label="最多分叉" value="most_forked" />
            <el-option label="最多浏览" value="most_viewed" />
          </el-select>
        </el-col>
        <el-col :span="6" class="text-right">
          <el-button :icon="Refresh" @click="fetchTemplates" :loading="isLoading">
            刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <div class="templates-grid mt-md" v-loading="isLoading" element-loading-text="加载中...">
      <el-row :gutter="16">
        <el-col :span="8" v-for="template in templates" :key="template.id" class="mb-md">
          <el-card class="template-card" shadow="hover">
            <div class="card-header">
              <h3 class="template-title">{{ template.name }}</h3>
              <el-tag size="small" type="info">{{ template.category }}</el-tag>
            </div>
            <p class="template-description">{{ template.description }}</p>
            <div class="template-tags">
              <el-tag
                v-for="tag in template.tags"
                :key="tag"
                size="small"
                effect="plain"
                class="mr-xs"
              >
                {{ tag }}
              </el-tag>
            </div>
            <div class="card-author">
              <el-avatar :size="32" :src="template.author_avatar">
                {{ template.author_name?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="author-name">{{ template.author_name }}</span>
            </div>
            <div class="card-stats">
              <span class="stat-item">
                <el-icon :size="14"><View /></el-icon>
                {{ template.views || 0 }}
              </span>
              <span class="stat-item">
                <el-icon :size="14"><Star /></el-icon>
                {{ template.likes || 0 }}
              </span>
              <span class="stat-item">
                <el-icon :size="14"><CopyDocument /></el-icon>
                {{ template.forks || 0 }}
              </span>
            </div>
            <div class="card-actions">
              <el-button size="small" @click="viewDetail(template)">
                详情
              </el-button>
              <el-button size="small" type="primary" @click="applyTemplate(template)">
                应用
              </el-button>
              <el-button
                size="small"
                :type="template.is_liked ? 'danger' : 'default'"
                @click="likeTemplate(template)"
              >
                <el-icon><Star :fill="template.is_liked ? 'currentColor' : 'none'" /></el-icon>
              </el-button>
              <el-button size="small" @click="forkTemplate(template)">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!isLoading && templates.length === 0" description="暂无模板" />
    </div>

    <div class="pagination-container mt-md" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[9, 18, 36]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog
      v-model="publishDialogVisible"
      title="发布模板"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="publishFormRef" :model="publishForm" :rules="publishRules" label-width="100px">
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="publishForm.name" placeholder="请输入模板名称" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="publishForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="publishForm.category" placeholder="请选择分类" style="width: 100%;">
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <div class="tags-input">
            <el-tag
              v-for="(tag, index) in publishForm.tags"
              :key="tag"
              closable
              size="small"
              class="mr-xs"
              @close="removeTag(index)"
            >
              {{ tag }}
            </el-tag>
            <el-input
              v-model="newTag"
              size="small"
              placeholder="添加标签"
              style="width: 120px;"
              @keyup.enter="addTag"
              @blur="addTag"
            />
          </div>
        </el-form-item>
        <el-form-item label="作者名称" prop="author_name">
          <el-input v-model="publishForm.author_name" placeholder="请输入作者名称" />
        </el-form-item>
        <el-form-item label="公开可见">
          <el-switch v-model="publishForm.is_public" />
        </el-form-item>
        <el-form-item label="附加内容">
          <el-checkbox v-model="publishForm.include_factor_stats">
            包含因子统计结果
          </el-checkbox>
          <el-checkbox v-model="publishForm.include_backtest_result" class="ml-md">
            包含回测结果
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="isPublishing" @click="handlePublish">
          发布
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="detailDialogVisible"
      title="模板详情"
      width="800px"
    >
      <div v-if="selectedTemplate" class="detail-content" v-loading="isLoadingDetail">
        <div class="detail-header">
          <h2>{{ selectedTemplate.name }}</h2>
          <el-tag size="small" type="info">{{ selectedTemplate.category }}</el-tag>
        </div>
        <p class="detail-description">{{ selectedTemplate.description }}</p>
        <div class="detail-tags">
          <el-tag
            v-for="tag in selectedTemplate.tags"
            :key="tag"
            size="small"
            effect="plain"
            class="mr-xs"
          >
            {{ tag }}
          </el-tag>
        </div>
        <div class="detail-author">
          <el-avatar :size="40" :src="selectedTemplate.author_avatar">
            {{ selectedTemplate.author_name?.charAt(0) || 'U' }}
          </el-avatar>
          <div>
            <div class="author-name">{{ selectedTemplate.author_name }}</div>
            <div class="publish-date">
              发布于 {{ formatDate(selectedTemplate.created_at) }}
            </div>
          </div>
        </div>
        <el-divider />
        <div class="detail-stats">
          <span class="stat-item">
            <el-icon :size="16"><View /></el-icon>
            {{ selectedTemplate.views || 0 }} 浏览
          </span>
          <span class="stat-item">
            <el-icon :size="16"><Star /></el-icon>
            {{ selectedTemplate.likes || 0 }} 点赞
          </span>
          <span class="stat-item">
            <el-icon :size="16"><Fork /></el-icon>
            {{ selectedTemplate.forks || 0 }} 分叉
          </span>
        </div>
        <el-divider />
        <div class="detail-workflow">
          <h4>工作流结构</h4>
          <div class="workflow-structure" v-if="selectedTemplate.workflow">
            <div class="workflow-nodes">
              <div class="section-title">节点 ({{ selectedTemplate.workflow.nodes?.length || 0 }})</div>
              <el-table :data="selectedTemplate.workflow.nodes" size="small" border>
                <el-table-column prop="id" label="ID" width="120" />
                <el-table-column prop="operator_id" label="算子" />
                <el-table-column label="参数">
                  <template #default="{ row }">
                    <span v-if="row.params && Object.keys(row.params).length > 0">
                      {{ Object.keys(row.params).length }} 个参数
                    </span>
                    <span v-else class="text-muted">无参数</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="workflow-edges mt-md">
              <div class="section-title">连接 ({{ selectedTemplate.workflow.edges?.length || 0 }})</div>
              <el-table :data="selectedTemplate.workflow.edges" size="small" border>
                <el-table-column prop="source" label="源节点" width="120" />
                <el-table-column prop="target" label="目标节点" width="120" />
                <el-table-column prop="target_input" label="输入端口" />
              </el-table>
            </div>
          </div>
          <el-empty v-else description="暂无工作流数据" :image-size="80" />
        </div>
        <div class="detail-backtest mt-md" v-if="selectedTemplate.backtest_result">
          <h4>回测结果</h4>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="年化收益率">
              {{ formatPercent(selectedTemplate.backtest_result.annual_return) }}
            </el-descriptions-item>
            <el-descriptions-item label="夏普比率">
              {{ formatNumber(selectedTemplate.backtest_result.sharpe_ratio, 2) }}
            </el-descriptions-item>
            <el-descriptions-item label="最大回撤">
              {{ formatPercent(selectedTemplate.backtest_result.max_drawdown) }}
            </el-descriptions-item>
            <el-descriptions-item label="胜率">
              {{ formatPercent(selectedTemplate.backtest_result.win_rate) }}
            </el-descriptions-item>
            <el-descriptions-item label="盈亏比">
              {{ formatNumber(selectedTemplate.backtest_result.profit_loss_ratio, 2) }}
            </el-descriptions-item>
            <el-descriptions-item label="总收益">
              {{ formatPercent(selectedTemplate.backtest_result.total_return) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="applyTemplate(selectedTemplate)">
          应用模板
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="forkDialogVisible"
      title="分叉模板"
      width="400px"
    >
      <el-form :model="forkForm" label-width="80px">
        <el-form-item label="新名称">
          <el-input v-model="forkForm.newName" placeholder="请输入新模板名称" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="forkForm.authorName" placeholder="请输入作者名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="forkDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="isForking" @click="confirmFork">
          确认分叉
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Search, Refresh, View, Star, CopyDocument
} from '@element-plus/icons-vue'
import { templateApi } from '../api'
import { useWorkflowStore } from '../stores/workflow'

const router = useRouter()
const workflowStore = useWorkflowStore()

const searchQuery = ref('')
const selectedCategory = ref(null)
const sortBy = ref('latest')
const currentPage = ref(1)
const pageSize = ref(9)
const total = ref(0)
const templates = ref([])
const categories = ref([])
const isLoading = ref(false)
const isLoadingDetail = ref(false)
const isPublishing = ref(false)
const isForking = ref(false)

const publishDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const forkDialogVisible = ref(false)

const selectedTemplate = ref(null)
const newTag = ref('')

const publishForm = reactive({
  name: '',
  description: '',
  category: '',
  tags: [],
  author_name: '',
  is_public: true,
  include_factor_stats: false,
  include_backtest_result: false
})

const publishRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入模板描述', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  author_name: [{ required: true, message: '请输入作者名称', trigger: 'blur' }]
}

const forkForm = reactive({
  newName: '',
  authorName: ''
})

const publishFormRef = ref(null)

async function fetchCategories() {
  try {
    const data = await templateApi.getCategories()
    categories.value = data.categories || data || []
  } catch (err) {
    console.error('Failed to fetch categories:', err)
    ElMessage.error('加载分类失败')
  }
}

async function fetchTemplates() {
  isLoading.value = true
  try {
    const params = {
      search: searchQuery.value || undefined,
      category: selectedCategory.value || undefined,
      sort_by: sortBy.value,
      offset: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const data = await templateApi.listTemplates(params)
    templates.value = data.templates || data.items || data || []
    total.value = data.total || templates.value.length
  } catch (err) {
    console.error('Failed to fetch templates:', err)
    ElMessage.error('加载模板列表失败')
    templates.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

async function viewDetail(template) {
  isLoadingDetail.value = true
  detailDialogVisible.value = true
  try {
    const data = await templateApi.getTemplate(template.id)
    selectedTemplate.value = data.template || data
  } catch (err) {
    console.error('Failed to fetch template detail:', err)
    ElMessage.error('加载模板详情失败')
    selectedTemplate.value = template
  } finally {
    isLoadingDetail.value = false
  }
}

async function applyTemplate(template) {
  try {
    const data = await templateApi.applyTemplate(template.id)
    const workflowData = data.workflow || data
    
    workflowStore.importTemplateWorkflow(workflowData)
    
    ElMessage.success('模板应用成功，正在跳转到工作台...')
    
    setTimeout(() => {
      router.push('/workbench')
    }, 500)
  } catch (err) {
    console.error('Failed to apply template:', err)
    ElMessage.error('应用模板失败: ' + (err.message || '未知错误'))
  }
}

async function likeTemplate(template) {
  try {
    await templateApi.likeTemplate(template.id)
    template.is_liked = !template.is_liked
    template.likes = (template.likes || 0) + (template.is_liked ? 1 : -1)
    ElMessage.success(template.is_liked ? '点赞成功' : '取消点赞')
  } catch (err) {
    console.error('Failed to like template:', err)
    ElMessage.error('操作失败')
  }
}

function forkTemplate(template) {
  selectedTemplate.value = template
  forkForm.newName = `${template.name} (分叉)`
  forkForm.authorName = ''
  forkDialogVisible.value = true
}

async function confirmFork() {
  if (!forkForm.newName.trim()) {
    ElMessage.warning('请输入新模板名称')
    return
  }
  if (!forkForm.authorName.trim()) {
    ElMessage.warning('请输入作者名称')
    return
  }

  isForking.value = true
  try {
    await templateApi.forkTemplate(
      selectedTemplate.value.id,
      forkForm.authorName,
      forkForm.newName
    )
    ElMessage.success('分叉成功')
    forkDialogVisible.value = false
    fetchTemplates()
  } catch (err) {
    console.error('Failed to fork template:', err)
    ElMessage.error('分叉失败: ' + (err.message || '未知错误'))
  } finally {
    isForking.value = false
  }
}

function openPublishDialog() {
  if (workflowStore.nodes.length === 0) {
    ElMessageBox.confirm(
      '当前工作流为空，无法发布模板。是否前往工作台创建工作流？',
      '提示',
      {
        confirmButtonText: '前往工作台',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      router.push('/workbench')
    }).catch(() => {})
    return
  }

  Object.assign(publishForm, {
    name: '',
    description: '',
    category: '',
    tags: [],
    author_name: '',
    is_public: true,
    include_factor_stats: false,
    include_backtest_result: false
  })
  newTag.value = ''
  publishDialogVisible.value = true
}

function addTag() {
  const tag = newTag.value.trim()
  if (tag && !publishForm.tags.includes(tag)) {
    if (publishForm.tags.length >= 5) {
      ElMessage.warning('最多添加5个标签')
      return
    }
    publishForm.tags.push(tag)
  }
  newTag.value = ''
}

function removeTag(index) {
  publishForm.tags.splice(index, 1)
}

async function handlePublish() {
  if (!publishFormRef.value) return

  try {
    await publishFormRef.value.validate()
  } catch (err) {
    return
  }

  isPublishing.value = true
  try {
    const workflow = workflowStore.exportWorkflow()
    const publishData = {
      ...publishForm,
      workflow,
      factor_stats: publishForm.include_factor_stats ? workflowStore.factorStats : null,
      backtest_result: publishForm.include_backtest_result ? workflowStore.backtestResult : null
    }

    await templateApi.publishTemplate(publishData)
    ElMessage.success('发布成功')
    publishDialogVisible.value = false
    fetchTemplates()
  } catch (err) {
    console.error('Failed to publish template:', err)
    ElMessage.error('发布失败: ' + (err.message || '未知错误'))
  } finally {
    isPublishing.value = false
  }
}

function handleSizeChange(val) {
  pageSize.value = val
  currentPage.value = 1
  fetchTemplates()
}

function handleCurrentChange(val) {
  currentPage.value = val
  fetchTemplates()
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

function formatNumber(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  return Number(v).toFixed(decimals)
}

function formatPercent(v) {
  if (v === null || v === undefined || isNaN(v)) return '-'
  const sign = v >= 0 ? '+' : ''
  return sign + (v * 100).toFixed(2) + '%'
}

onMounted(() => {
  fetchCategories()
  fetchTemplates()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  overflow: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filter-card {
  padding: 16px;
}

.text-right {
  text-align: right;
}

.templates-grid {
  min-height: 400px;
}

.template-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.template-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  margin-right: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-description {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
}

.template-tags {
  margin: 8px 0;
  min-height: 24px;
}

.card-author {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.author-name {
  font-size: 13px;
  color: #606266;
}

.card-stats {
  display: flex;
  gap: 16px;
  margin: 8px 0;
  padding: 8px 0;
  border-top: 1px solid #ebeef5;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
}

.card-actions .el-button {
  flex: 1;
}

.pagination-container {
  display: flex;
  justify-content: center;
}

.tags-input {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.mr-xs {
  margin-right: 4px;
}

.ml-md {
  margin-left: 12px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.detail-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.detail-description {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin: 16px 0;
}

.detail-tags {
  margin: 16px 0;
}

.detail-author {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
}

.detail-author .author-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.publish-date {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.detail-stats {
  display: flex;
  gap: 24px;
  margin: 16px 0;
}

.detail-stats .stat-item {
  font-size: 14px;
}

.detail-workflow h4,
.detail-backtest h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.workflow-structure {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
}

.text-muted {
  color: #c0c4cc;
}
</style>
