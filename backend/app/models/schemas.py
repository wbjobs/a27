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


class FactorComputeResponse(BaseModel):
    success: bool
    message: str
    factor_values: Optional[List[Dict[str, Any]]] = None
    stats: Optional[Dict[str, Any]] = None


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
