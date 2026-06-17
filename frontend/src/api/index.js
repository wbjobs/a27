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

export default api
