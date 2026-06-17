# 股票因子挖掘工作台 (Stock Factor Workbench)

基于 **DuckDB + Observable + FastAPI** 的交互式股票因子挖掘与回测工作台。

## 🏗️ 技术架构

| 层级 | 技术选型 | 职责 |
|------|----------|------|
| 前端 | Vue 3 + Pinia + Element Plus | UI交互 |
| 工作流 | 原生拖拽 + SVG连线 | 可视化因子构建 |
| 可视化 | D3.js + Observable Runtime | 图表渲染 |
| API服务 | FastAPI + Pydantic v2 | REST接口 |
| 计算引擎 | DuckDB + Pandas/NumPy | 内存OLAP分析 |
| 缓存层 | Redis (可选) | 计算结果缓存 |
| 统计计算 | SciPy | IC值、T检验等 |

## ✨ 核心功能

### 1. 数据管理
- **CSV / Parquet 导入**：一键导入日线/分钟线行情数据
- **智能列识别**：自动识别ts_code、trade_date、OHLC、成交量等字段
- **示例数据生成**：一键生成5-500只股票、20-2520交易日的模拟行情
- **DuckDB内存存储**：列式存储 + 向量化查询，亿级数据秒级响应

### 2. 拖拽式因子构建
支持 11+ 内置因子算子，可任意组合：

| 类别 | 算子 |
|------|------|
| 趋势指标 | MA移动平均、EMA指数移动平均、MACD |
| 动量指标 | Momentum动量 (比值/差值/收益率) |
| 超买超卖 | RSI相对强弱指数 |
| 波动率 | Bollinger布林带、Volatility波动率 |
| 成交量 | Volume Ratio成交量比率 |
| 基础指标 | PriceChange价格变化率 |
| 组合运算 | Arithmetic加减乘除 |
| 标准化 | Min-Max/Z-Score/Rank排序标准化 |

### 3. 因子回测引擎
- **IC值分析**：Spearman秩相关、ICIR信息比率、T检验
- **分组收益率**：2-20组灵活分组、多空组合
- **换手率分析**：分组持仓变化、摩擦成本扣除
- **绩效指标**：年化收益、夏普比率、最大回撤

### 4. D3.js 可视化
- 📈 **分组累计收益曲线**：多组对比 + 图例
- 📊 **IC时序柱状图**：P值显著性高亮
- 🔥 **分组收益热力图**：RdYlGn渐变色阶
- 📉 **换手率面积图**：平均值参考线
- 💹 **多空组合曲线**：当日收益散点

## 📁 项目结构

```
a27/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                 # 配置管理
│   │   ├── main.py                   # FastAPI入口
│   │   ├── api/                      # API路由
│   │   │   ├── data_router.py        # 数据管理接口
│   │   │   ├── factor_router.py      # 因子计算接口
│   │   │   └── backtest_router.py    # 回测接口
│   │   ├── core/                     # 核心引擎
│   │   │   ├── duckdb_engine.py      # DuckDB封装
│   │   │   ├── cache.py              # Redis缓存层
│   │   │   ├── operators.py          # 因子算子库
│   │   │   ├── factor_engine.py      # 工作流执行器
│   │   │   └── backtest_engine.py    # 回测引擎
│   │   └── models/
│   │       └── schemas.py            # Pydantic数据模型
│   └── requirements.txt              # Python依赖
│
└── frontend/                         # Vue 3 前端
    ├── src/
    │   ├── main.js                   # Vue入口
    │   ├── App.vue                   # 主布局组件
    │   ├── api/index.js              # Axios封装
    │   ├── stores/workflow.js        # Pinia状态管理
    │   ├── styles/main.scss          # 全局样式
    │   └── components/
    │       ├── OperatorPalette.vue   # 算子面板（拖拽源）
    │       ├── WorkflowCanvas.vue    # 工作流画布（SVG+缩放）
    │       ├── FactorNode.vue        # 可配置算子节点
    │       ├── NodePropertyPanel.vue # 节点属性编辑
    │       ├── FactorResultPanel.vue # 因子计算结果
    │       ├── BacktestPanel.vue     # 回测指标摘要
    │       └── ResultViewer.vue      # D3可视化（5种图表）
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 🚀 快速开始

### 前置条件
- Python 3.10+
- Node.js 16+
- Redis 6+ (可选，未安装自动降级为无缓存模式)

### 启动后端服务

```bash
cd backend
pip install -r requirements.txt

# 运行（开发模式，自动热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/docs` 查看Swagger API文档。

### 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 打开工作台。

### Redis配置（可选）

如果没有安装Redis，系统会自动跳过缓存功能。配置环境变量：
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_ENABLED=true
```

## 📖 使用指南

### 基础工作流

1. **生成/导入数据** → 点击「生成示例数据」或导入CSV/Parquet
2. **拖拽算子** → 从左侧面板拖到中间画布
3. **连接节点** → 从输出端口（右侧）拖到输入端口（左侧）
4. **设置参数** → 点击节点，右侧面板调整参数
5. **设为输出** → 点击节点头部的★图标
6. **计算因子** → 选择数据集后点击「计算因子」
7. **一键回测** → 点击「一键回测」查看IC、分组收益
8. **查看图表** → 点击「查看可视化图表」打开D3看板

### 数据格式要求

CSV/Parquet文件需包含以下列（支持中英文列名）：

| 列名 | 别名 | 类型 | 说明 |
|------|------|------|------|
| ts_code | code, symbol, stock_code | string | 股票代码，如 `600000.SH` |
| trade_date | date, time | date | 交易日 `YYYY-MM-DD` |
| open | 开盘 | float | 开盘价 |
| high | 最高 | float | 最高价 |
| low | 最低 | float | 最低价 |
| close | 收盘 | float | 收盘价 |
| volume | vol, 成交量 | float | 成交量（股） |

### 构建复杂因子示例：双均线交叉 + RSI 确认

```
节点1: MA(period=5)    ← close收盘价
节点2: MA(period=20)   ← close收盘价
节点3: 算术运算(sub)   ← 节点1输出 - 节点2输出 （得到价差）
节点4: RSI(period=14)  ← close收盘价
节点5: 排序标准化(Z)   ← 节点4输出
节点6: 算术运算(add)   ← 节点3输出 + 节点5输出 ★ 设为输出
```

## 🔌 API速览

### 数据管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/data/import` | 上传CSV/Parquet |
| GET | `/api/data/datasets` | 列出数据集 |
| POST | `/api/data/generate-sample` | 生成模拟行情 |

### 因子计算
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/factor/operators` | 获取算子列表 |
| POST | `/api/factor/compute` | 执行因子工作流 |
| POST | `/api/factor/validate-workflow` | 验证工作流拓扑 |

### 回测分析
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/backtest/run` | 完整因子回测 |
| POST | `/api/backtest/quick-analysis` | 因子值快速统计 |

## 🧮 核心数学模型

### IC值（信息系数）
每日截面Spearman秩相关：
```
IC_t = RankCorr(Factor_t, Return_{t+1})
ICIR = Mean(IC) / Std(IC) × √252
```

### 分组回测
1. 每日按因子值升序分N组（qcut分位数）
2. 计算每组下一期等权平均收益
3. 扣除换手率×手续费摩擦成本
4. 多空收益 = G_max - G_min

### 绩效指标
```
年化收益 = (1 + 累计收益) ^ (252 / N) - 1
夏普比率  = (Mean(r) / Std(r)) × √252
最大回撤  = Min((Cum - Max(Cum)) / Max(Cum))
```

## 🔧 扩展开发

### 添加自定义因子算子

在 `backend/app/core/operators.py` 中继承 `FactorOperatorBase`：

```python
class MyFactor(FactorOperatorBase):
    operator_id = "my_factor"
    name = "自定义因子"
    category = "自定义"
    description = "示例自定义因子"
    inputs = [{"id": "price", "name": "价格", "type": "series", "required": True}]
    outputs = [{"id": "result", "name": "输出值", "type": "series"}]
    params = [{"id": "p", "name": "参数", "type": "int", "default": 10}]
    
    def compute(self, inputs, params):
        price = inputs["price"]
        p = int(params.get("p", 10))
        # 你的计算逻辑...
        return price.rolling(p).apply(lambda x: some_logic(x))

OperatorRegistry.register(MyFactor())
```

无需改前端代码，刷新后算子面板自动出现。

## 📄 License

MIT License
