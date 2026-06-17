from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


class Frequency(str, Enum):
    DAILY = "daily"
    MINUTE = "minute"


class StockPool(str, Enum):
    HS300 = "hs300"
    ZZ500 = "zz500"
    ZZ1000 = "zz1000"
    ALL = "all"
    CUSTOM = "custom"


class BarData(BaseModel):
    ts_code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    amount: Optional[float] = None


class DataImportRequest(BaseModel):
    file_type: str = Field(..., description="文件类型: csv 或 parquet")
    frequency: Frequency = Frequency.DAILY
    stock_pool: StockPool = StockPool.ALL


class DataImportResponse(BaseModel):
    success: bool
    message: str
    table_name: Optional[str] = None
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None


class DatasetInfo(BaseModel):
    name: str
    row_count: int
    columns: List[str]
    frequency: Frequency
    date_range: Optional[Dict[str, date]] = None


class FactorOperator(BaseModel):
    id: str
    name: str
    category: str
    description: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    params: List[Dict[str, Any]]
    lookback: int = 0


class FactorNode(BaseModel):
    id: str
    operator_id: str
    params: Dict[str, Any] = {}
    inputs: Dict[str, Any] = {}


class FactorWorkflow(BaseModel):
    name: str
    nodes: List[FactorNode]
    output_node: str
    description: Optional[str] = None


class FactorComputeRequest(BaseModel):
    workflow: FactorWorkflow
    dataset_name: str
    stock_codes: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    forward_validation: bool = Field(default=False, description="启用严格前向验证模式，杜绝未来函数")


class FactorComputeResponse(BaseModel):
    success: bool
    message: str
    factor_values: Optional[List[Dict[str, Any]]] = None
    stats: Optional[Dict[str, Any]] = None
    forward_validation: Optional[Dict[str, Any]] = None


class FactorCorrelationRequest(BaseModel):
    factor_values_list: List[Dict[str, Any]] = Field(..., description="多个因子值列表，每个包含name和values")
    dataset_name: str
    vif_threshold: float = Field(default=10.0, ge=1.0, le=100.0, description="VIF阈值，超过此值认为存在严重共线性")
    corr_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相关系数阈值，超过此值认为高度相关")


class FactorCorrelationResult(BaseModel):
    success: bool
    message: str
    correlation_matrix: Optional[List[Dict[str, Any]]] = None
    vif_values: Optional[List[Dict[str, Any]]] = None
    collinear_pairs: Optional[List[Dict[str, Any]]] = None
    removed_factors: Optional[List[str]] = None
    kept_factors: Optional[List[str]] = None


class BacktestRequest(BaseModel):
    factor_name: str
    factor_values: List[Dict[str, Any]]
    dataset_name: str
    n_groups: int = Field(default=5, ge=2, le=20)
    holding_period: int = Field(default=1, ge=1, le=60)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    commission_rate: float = Field(default=0.0003, ge=0, le=0.01)


class ICStats(BaseModel):
    mean_ic: float
    ic_std: float
    icir: float
    t_stat: float
    p_value: float
    ic_values: List[Dict[str, Any]]


class GroupReturns(BaseModel):
    group: int
    cumulative_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    returns: List[Dict[str, Any]]
    cumulative_returns: List[Dict[str, Any]]


class TurnoverStats(BaseModel):
    mean_turnover: float
    turnover_std: float
    turnover_by_period: List[Dict[str, Any]]


class BacktestResult(BaseModel):
    success: bool
    message: str
    ic_stats: Optional[ICStats] = None
    group_returns: Optional[List[GroupReturns]] = None
    long_short_return: Optional[Dict[str, Any]] = None
    turnover_stats: Optional[TurnoverStats] = None
    heatmap_data: Optional[List[Dict[str, Any]]] = None


# ============================================
# 实时行情 WebSocket 模型
# ============================================
class RealtimeBar(BaseModel):
    ts_code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: float


class RealtimeFactorUpdate(BaseModel):
    ts_code: str
    trade_date: date
    factor_value: float
    previous_value: float
    change_pct: float


class WebsocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: float


# ============================================
# 组合优化模型
# ============================================
class PortfolioFactorInput(BaseModel):
    name: str
    factor_values: List[Dict[str, Any]]


class OptimizationModel(str, Enum):
    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"


class PortfolioRequest(BaseModel):
    dataset_name: str
    factors: List[PortfolioFactorInput]
    model: OptimizationModel = OptimizationModel.MEAN_VARIANCE
    risk_free_rate: float = Field(default=0.03, ge=0, le=0.2)
    target_return: Optional[float] = None
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    max_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    rebalance_freq: str = "monthly"


class EfficientFrontierPoint(BaseModel):
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class PortfolioResult(BaseModel):
    success: bool
    message: str
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    efficient_frontier: Optional[List[EfficientFrontierPoint]] = None
    monte_carlo_points: Optional[List[Dict[str, Any]]] = None
    risk_contributions: Optional[Dict[str, float]] = None


# ============================================
# SHAP 因子解释模型
# ============================================
class ShapRequest(BaseModel):
    dataset_name: str
    factor_name: str
    factor_values: List[Dict[str, Any]]
    n_samples: int = Field(default=100, ge=10, le=5000)
    target_period: int = Field(default=5, ge=1, le=60)


class FeatureContribution(BaseModel):
    feature: str
    mean_shap_value: float
    mean_abs_shap_value: float
    importance_rank: int


class ShapResult(BaseModel):
    success: bool
    message: str
    feature_contributions: List[FeatureContribution]
    shap_values: List[Dict[str, Any]]
    base_value: float
    summary_plot_data: List[Dict[str, Any]]
    force_plot_data: List[Dict[str, Any]]


# ============================================
# 模板市场模型
# ============================================
class TemplateAuthor(BaseModel):
    name: str
    avatar: Optional[str] = None
    profile: Optional[str] = None


class FactorTemplate(BaseModel):
    template_id: Optional[str] = None
    name: str
    description: str
    category: str
    tags: List[str] = []
    author: TemplateAuthor
    workflow: FactorWorkflow
    factor_stats: Optional[Dict[str, Any]] = None
    backtest_result: Optional[Dict[str, Any]] = None
    likes: int = 0
    forks: int = 0
    views: int = 0
    is_public: bool = True
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class TemplatePublishRequest(BaseModel):
    name: str
    description: str
    category: str
    tags: List[str] = []
    author_name: str
    workflow: FactorWorkflow
    factor_stats: Optional[Dict[str, Any]] = None
    backtest_result: Optional[Dict[str, Any]] = None
    is_public: bool = True


class TemplateListResponse(BaseModel):
    success: bool
    message: str
    total: int
    templates: List[FactorTemplate]


class TemplateForkResponse(BaseModel):
    success: bool
    message: str
    new_template_id: str
    workflow: FactorWorkflow

