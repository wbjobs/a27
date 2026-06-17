import { createRouter, createWebHashHistory } from 'vue-router'
import WorkbenchPage from '../views/WorkbenchPage.vue'
import PortfolioPage from '../views/PortfolioPage.vue'
import ShapAnalysisPage from '../views/ShapAnalysisPage.vue'
import TemplateMarketPage from '../views/TemplateMarketPage.vue'
import RealtimePage from '../views/RealtimePage.vue'

const routes = [
  {
    path: '/',
    name: 'Workbench',
    component: WorkbenchPage
  },
  {
    path: '/portfolio',
    name: 'Portfolio',
    component: PortfolioPage
  },
  {
    path: '/shap',
    name: 'ShapAnalysis',
    component: ShapAnalysisPage
  },
  {
    path: '/templates',
    name: 'TemplateMarket',
    component: TemplateMarketPage
  },
  {
    path: '/realtime',
    name: 'Realtime',
    component: RealtimePage
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
