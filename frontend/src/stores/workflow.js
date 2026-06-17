import { defineStore } from 'pinia'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    nodes: [],
    edges: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    outputNodeId: null,
    draggingFrom: null,
    tempEdge: null,
    pan: { x: 0, y: 0 },
    scale: 1,
    nextNodeId: 1,
    operators: [],
    operatorsByCategory: {},
    currentDataset: null,
    factorResult: null,
    factorStats: null,
    backtestResult: null,
    datasets: [],
    isLoading: false
  }),

  getters: {
    selectedNode: (state) =>
      state.nodes.find((n) => n.id === state.selectedNodeId),
    getNodeById: (state) => (id) =>
      state.nodes.find((n) => n.id === id),
    getOperatorById: (state) => (id) =>
      state.operators.find((o) => o.id === id),
    workflowName: () => '自定义因子工作流'
  },

  actions: {
    setOperators(operators, byCategory) {
      this.operators = operators
      this.operatorsByCategory = byCategory
    },

    setDatasets(datasets) {
      this.datasets = datasets
    },

    setCurrentDataset(dataset) {
      this.currentDataset = dataset
    },

    generateNodeId() {
      return `node_${this.nextNodeId++}`
    },

    addNode(operatorId, x, y) {
      const operator = this.getOperatorById(operatorId)
      if (!operator) return null

      const node = {
        id: this.generateNodeId(),
        operator_id: operatorId,
        name: operator.name,
        category: operator.category,
        x,
        y,
        params: {},
        inputs: {}
      }

      operator.params.forEach((p) => {
        node.params[p.id] = p.default
      })

      // Initialize default market data inputs based on input id
      operator.inputs.forEach((inp) => {
        const inpId = inp.id.toLowerCase()
        if (inpId.includes('price') || inpId.includes('factor') || inpId === 'left' || inpId === 'right' || inpId === 'a' || inpId === 'b') {
          node.inputs[inp.id] = { type: 'market_data', field: 'close' }
        } else if (inpId.includes('vol')) {
          node.inputs[inp.id] = { type: 'market_data', field: 'volume' }
        }
      })

      this.nodes.push(node)

      if (!this.outputNodeId) {
        this.outputNodeId = node.id
      }

      return node
    },

    removeNode(nodeId) {
      this.nodes = this.nodes.filter((n) => n.id !== nodeId)
      this.edges = this.edges.filter(
        (e) => e.source !== nodeId && e.target !== nodeId
      )
      if (this.selectedNodeId === nodeId) {
        this.selectedNodeId = null
      }
      if (this.outputNodeId === nodeId) {
        this.outputNodeId = this.nodes.length > 0 ? this.nodes[this.nodes.length - 1].id : null
      }
      this.rebuildNodeInputs()
    },

    updateNodePosition(nodeId, x, y) {
      const node = this.getNodeById(nodeId)
      if (node) {
        node.x = x
        node.y = y
      }
    },

    updateNodeParam(nodeId, paramId, value) {
      const node = this.getNodeById(nodeId)
      if (node) {
        node.params[paramId] = value
      }
    },

    selectNode(nodeId) {
      this.selectedNodeId = nodeId
      this.selectedEdgeId = null
    },

    clearSelection() {
      this.selectedNodeId = null
      this.selectedEdgeId = null
    },

    setOutputNode(nodeId) {
      if (this.nodes.some((n) => n.id === nodeId)) {
        this.outputNodeId = nodeId
      }
    },

    addEdge(source, target, targetInput, sourceOutput = 'result') {
      const exists = this.edges.some(
        (e) => e.source === source && e.target === target && e.target_input === targetInput
      )
      if (exists) return false

      this.edges = this.edges.filter(
        (e) => !(e.target === target && e.target_input === targetInput)
      )

      const edge = {
        id: `edge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        source,
        target,
        target_input: targetInput,
        source_output: sourceOutput
      }
      this.edges.push(edge)
      this.rebuildNodeInputs()
      return true
    },

    removeEdge(edgeId) {
      this.edges = this.edges.filter((e) => e.id !== edgeId)
      if (this.selectedEdgeId === edgeId) {
        this.selectedEdgeId = null
      }
      this.rebuildNodeInputs()
    },

    selectEdge(edgeId) {
      this.selectedEdgeId = edgeId
      this.selectedNodeId = null
    },

    rebuildNodeInputs() {
      const nodeInputs = {}
      this.nodes.forEach((n) => {
        nodeInputs[n.id] = {}
        // Preserve existing market_data inputs
        Object.entries(n.inputs || {}).forEach(([key, val]) => {
          if (val && typeof val === 'object' && val.type === 'market_data') {
            nodeInputs[n.id][key] = val
          }
        })
      })
      // Apply edges as node_output type inputs
      this.edges.forEach((e) => {
        if (nodeInputs[e.target]) {
          nodeInputs[e.target][e.target_input] = {
            type: 'node_output',
            node_id: e.source,
            output_id: e.source_output || 'result'
          }
        }
      })
      this.nodes.forEach((n) => {
        n.inputs = nodeInputs[n.id] || {}
      })
    },

    startDraggingEdge(nodeId, outputId, startX, startY) {
      this.draggingFrom = { nodeId, outputId, startX, startY }
      this.tempEdge = {
        x1: startX,
        y1: startY,
        x2: startX,
        y2: startY
      }
    },

    updateTempEdge(x2, y2) {
      if (this.tempEdge) {
        this.tempEdge.x2 = x2
        this.tempEdge.y2 = y2
      }
    },

    finishDraggingEdge(targetNodeId, targetInputId) {
      if (this.draggingFrom && targetNodeId && targetInputId) {
        if (this.draggingFrom.nodeId !== targetNodeId) {
          this.addEdge(
            this.draggingFrom.nodeId,
            targetNodeId,
            targetInputId,
            this.draggingFrom.outputId || 'result'
          )
        }
      }
      this.draggingFrom = null
      this.tempEdge = null
    },

    cancelDraggingEdge() {
      this.draggingFrom = null
      this.tempEdge = null
    },

    setPan(x, y) {
      this.pan.x = x
      this.pan.y = y
    },

    setScale(scale) {
      this.scale = Math.max(0.25, Math.min(2, scale))
    },

    exportWorkflow() {
      return {
        name: this.workflowName,
        nodes: this.nodes.map((n) => ({
          id: n.id,
          operator_id: n.operator_id,
          params: { ...n.params },
          inputs: { ...n.inputs }
        })),
        edges: this.edges.map((e) => ({
          id: e.id,
          source_node: e.source,
          source_port: e.source_output || 'result',
          target_node: e.target,
          target_port: e.target_input
        })),
        output_node: this.outputNodeId
      }
    },

    loadWorkflow(workflow) {
      this.nodes = workflow.nodes.map((n, i) => ({
        ...n,
        x: 100 + (i % 3) * 280,
        y: 100 + Math.floor(i / 3) * 200,
        category: this.getOperatorById(n.operator_id)?.category || 'basic',
        name: this.getOperatorById(n.operator_id)?.name || n.operator_id
      }))
      this.outputNodeId = workflow.output_node
      this.edges = []
      this.nextNodeId = Math.max(...workflow.nodes.map((n) => parseInt(n.id.split('_')[1]) || 0), 0) + 1
      this.rebuildNodeInputs()
    },

    clearWorkflow() {
      this.nodes = []
      this.edges = []
      this.selectedNodeId = null
      this.selectedEdgeId = null
      this.outputNodeId = null
      this.factorResult = null
      this.factorStats = null
      this.backtestResult = null
      this.nextNodeId = 1
      this.syncToUrl()
    },

    setFactorResult(values, stats) {
      this.factorResult = values
      this.factorStats = stats
    },

    setBacktestResult(result) {
      this.backtestResult = result
    },

    setLoading(loading) {
      this.isLoading = loading
    },

    syncToUrl() {
      try {
        if (this.nodes.length === 0) {
          const currentUrl = new URL(window.location.href)
          currentUrl.hash = ''
          window.history.replaceState(null, '', currentUrl.toString())
          return
        }

        const state = {
          n: this.nodes.map(nd => ({
            id: nd.id,
            oid: nd.operator_id,
            x: Math.round(nd.x),
            y: Math.round(nd.y),
            p: nd.params
          })),
          e: this.edges.map(ed => ({
            s: ed.source,
            si: ed.source_output,
            t: ed.target,
            ti: ed.target_input
          })),
          o: this.outputNodeId
        }

        const json = JSON.stringify(state)
        const encoded = btoa(unescape(encodeURIComponent(json)))
        const currentUrl = new URL(window.location.href)
        currentUrl.hash = 'wf=' + encoded
        window.history.replaceState(null, '', currentUrl.toString())
      } catch (err) {
        console.warn('Failed to sync workflow to URL:', err)
      }
    },

    loadFromUrl() {
      try {
        const hash = window.location.hash
        if (!hash || !hash.startsWith('#wf=')) return false

        const encoded = hash.slice(4)
        const json = decodeURIComponent(escape(atob(encoded)))
        const state = JSON.parse(json)

        if (!state.n || !Array.isArray(state.n)) return false

        this.nodes = state.n.map(nd => {
          const op = this.operators.find(o => o.id === nd.oid)
          const inputs = {}
          if (op) {
            op.inputs.forEach(inp => {
              const inpId = inp.id.toLowerCase()
              if (inpId.includes('price') || inpId.includes('factor') || inpId === 'left' || inpId === 'right') {
                inputs[inp.id] = { type: 'market_data', field: 'close' }
              } else if (inpId.includes('vol')) {
                inputs[inp.id] = { type: 'market_data', field: 'volume' }
              }
            })
          }
          return {
            id: nd.id,
            operator_id: nd.oid,
            name: op?.name || nd.oid,
            category: op?.category || 'basic',
            x: nd.x,
            y: nd.y,
            params: nd.p || {},
            inputs
          }
        })

        this.edges = (state.e || []).map((ed, i) => ({
          id: `edge_url_${i}`,
          source: ed.s,
          source_output: ed.si,
          target: ed.t,
          target_input: ed.ti
        }))

        this.outputNodeId = state.o || null
        this.nextNodeId = Math.max(...this.nodes.map(n => parseInt(n.id.split('_')[1]) || 0), 0) + 1
        this.rebuildNodeInputs()
        return true
      } catch (err) {
        console.warn('Failed to load workflow from URL:', err)
        return false
      }
    },

    getShareUrl() {
      this.syncToUrl()
      return window.location.href
    }
  }
})
