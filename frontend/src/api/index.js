import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export const dataApi = {
  importData: (file, fileType, frequency) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/data/import', formData, {
      params: { file_type: fileType, frequency },
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  listDatasets: () => api.get('/data/datasets'),
  getDatasetInfo: (name) => api.get(`/data/datasets/${name}`),
  deleteDataset: (name) => api.delete(`/data/datasets/${name}`),
  previewDataset: (name, limit = 100) => api.get(`/data/datasets/${name}/preview`, { params: { limit } }),
  listStocks: (name, limit = 500) => api.get(`/data/datasets/${name}/stocks`, { params: { limit } }),
  generateSample: (nStocks = 50, nDays = 252, datasetName = null) =>
    api.post('/data/generate-sample', null, {
      params: { n_stocks: nStocks, n_days: nDays, dataset_name: datasetName }
    })
}

export const factorApi = {
  listOperators: () => api.get('/factor/operators'),
  getOperator: (id) => api.get(`/factor/operators/${id}`),
  computeFactor: (workflow, datasetName, stockCodes = null, startDate = null, endDate = null, forwardValidation = false) =>
    api.post('/factor/compute', {
      workflow,
      dataset_name: datasetName,
      stock_codes: stockCodes,
      start_date: startDate,
      end_date: endDate,
      forward_validation: forwardValidation
    }),
  validateWorkflow: (workflow) => api.post('/factor/validate-workflow', workflow),
  analyzeCorrelation: (factorValuesList, datasetName, vifThreshold = 10, corrThreshold = 0.7) =>
    api.post('/factor/correlation', {
      factor_values_list: factorValuesList,
      dataset_name: datasetName,
      vif_threshold: vifThreshold,
      corr_threshold: corrThreshold
    })
}

export const backtestApi = {
  runBacktest: (params) => api.post('/backtest/run', params),
  quickAnalysis: (factorValues) => api.post('/backtest/quick-analysis', { factor_values: factorValues })
}

export const portfolioApi = {
  listModels: () => api.get('/portfolio/models'),
  optimize: (datasetName, factors, model = 'mean_variance', riskFreeRate = 0.03, targetReturn = null, minWeight = 0, maxWeight = 1) =>
    api.post('/portfolio/optimize', {
      dataset_name: datasetName,
      factors,
      model,
      risk_free_rate: riskFreeRate,
      target_return: targetReturn,
      min_weight: minWeight,
      max_weight: maxWeight
    })
}

export const shapApi = {
  analyze: (datasetName, factorName, factorValues, nSamples = 100, targetPeriod = 5) =>
    api.post('/shap/analyze', {
      dataset_name: datasetName,
      factor_name: factorName,
      factor_values: factorValues,
      n_samples: nSamples,
      target_period: targetPeriod
    }),
  generateReport: (factorName, shapResult, backtestResult) =>
    api.post('/shap/report', {
      factor_name: factorName,
      shap_result: shapResult,
      backtest_result: backtestResult
    }, {
      responseType: 'blob'
    })
}

export const templateApi = {
  listTemplates: (params) => api.get('/templates', { params }),
  getCategories: () => api.get('/templates/categories'),
  getTemplate: (id) => api.get(`/templates/${id}`),
  publishTemplate: (data) => api.post('/templates/publish', data),
  forkTemplate: (id, authorName, newName) => api.post(`/templates/${id}/fork`, null, { params: { author_name: authorName, new_name: newName } }),
  likeTemplate: (id) => api.post(`/templates/${id}/like`),
  deleteTemplate: (id) => api.delete(`/templates/${id}`),
  applyTemplate: (id) => api.post(`/templates/${id}/apply`)
}

export const wsApi = {
  buildRealtimeUrl: (datasetName, workflow, pushInterval = 1.0) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname + ':8000'
    const workflowStr = encodeURIComponent(JSON.stringify(workflow))
    return `${protocol}//${host}/ws/realtime?dataset_name=${encodeURIComponent(datasetName)}&workflow=${workflowStr}&push_interval=${pushInterval}`
  }
}

export default api
