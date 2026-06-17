import pandas as pd
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
from abc import ABC, abstractmethod


class FactorOperatorBase(ABC):
    operator_id: str = ""
    name: str = ""
    category: str = ""
    description: str = ""
    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []
    params: List[Dict[str, Any]] = []
    lookback: int = 0

    @abstractmethod
    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        pass

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return self.lookback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.operator_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "params": self.params,
            "lookback": self.lookback
        }


class MovingAverage(FactorOperatorBase):
    operator_id = "ma"
    name = "移动平均 (MA)"
    category = "趋势指标"
    description = "计算简单移动平均线"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "ma", "name": "移动平均值", "type": "series"}]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 20, "min": 1, "max": 500}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 20))

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 20))
        return price.rolling(window=period, min_periods=1).mean()


class ExponentialMovingAverage(FactorOperatorBase):
    operator_id = "ema"
    name = "指数移动平均 (EMA)"
    category = "趋势指标"
    description = "计算指数移动平均线"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "ema", "name": "指数移动平均", "type": "series"}]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 20, "min": 1, "max": 500}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 20)) * 3

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 20))
        return price.ewm(span=period, adjust=False).mean()


class RelativeStrengthIndex(FactorOperatorBase):
    operator_id = "rsi"
    name = "相对强弱指数 (RSI)"
    category = "超买超卖指标"
    description = "计算RSI指标，衡量价格变动的速度和变化"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "rsi", "name": "RSI值", "type": "series"}]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 14, "min": 2, "max": 100}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 14)) + 1

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 14))
        delta = price.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class BollingerBands(FactorOperatorBase):
    operator_id = "bollinger"
    name = "布林带 (Bollinger Bands)"
    category = "波动率指标"
    description = "计算布林带上中下轨"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [
        {"id": "upper", "name": "上轨", "type": "series"},
        {"id": "middle", "name": "中轨", "type": "series"},
        {"id": "lower", "name": "下轨", "type": "series"},
        {"id": "bandwidth", "name": "带宽", "type": "series"},
        {"id": "position", "name": "位置值", "type": "series"}
    ]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 20, "min": 2, "max": 500},
        {"id": "std_dev", "name": "标准差倍数", "type": "float", "default": 2.0, "min": 0.1, "max": 5.0}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 20))

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 20))
        std_dev = float(params.get("std_dev", 2.0))
        
        middle = price.rolling(window=period, min_periods=1).mean()
        std = price.rolling(window=period, min_periods=1).std()
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        bandwidth = (upper - lower) / middle.replace(0, np.nan)
        position = (price - lower) / (upper - lower).replace(0, np.nan)
        
        return position


class Momentum(FactorOperatorBase):
    operator_id = "momentum"
    name = "动量 (Momentum)"
    category = "动量指标"
    description = "计算价格动量，即当前价与N日前价的差值或比值"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "momentum", "name": "动量值", "type": "series"}]
    params = [
        {"id": "period", "name": "回溯周期", "type": "int", "default": 20, "min": 1, "max": 500},
        {"id": "method", "name": "计算方式", "type": "select", "default": "ratio",
         "options": [{"label": "比值", "value": "ratio"}, {"label": "差值", "value": "diff"}, {"label": "收益率", "value": "return"}]}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 20))

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 20))
        method = params.get("method", "ratio")
        
        prev = price.shift(period)
        if method == "ratio":
            return price / prev.replace(0, np.nan)
        elif method == "diff":
            return price - prev
        else:
            return (price - prev) / prev.replace(0, np.nan)


class MACD(FactorOperatorBase):
    operator_id = "macd"
    name = "MACD"
    category = "趋势指标"
    description = "计算MACD指标"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [
        {"id": "dif", "name": "DIF线", "type": "series"},
        {"id": "dea", "name": "DEA线", "type": "series"},
        {"id": "hist", "name": "柱状图", "type": "series"}
    ]
    params = [
        {"id": "fast", "name": "快线周期", "type": "int", "default": 12, "min": 2, "max": 200},
        {"id": "slow", "name": "慢线周期", "type": "int", "default": 26, "min": 2, "max": 500},
        {"id": "signal", "name": "信号线周期", "type": "int", "default": 9, "min": 2, "max": 100}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        slow = int(params.get("slow", 26))
        signal = int(params.get("signal", 9))
        return slow * 3 + signal

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        signal = int(params.get("signal", 9))
        
        ema_fast = price.ewm(span=fast, adjust=False).mean()
        ema_slow = price.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2 * (dif - dea)
        return hist


class VolumeRatio(FactorOperatorBase):
    operator_id = "volume_ratio"
    name = "成交量比率"
    category = "成交量指标"
    description = "当前成交量与平均成交量的比值"
    inputs = [{"id": "volume", "name": "成交量", "type": "series", "required": True}]
    outputs = [{"id": "vr", "name": "成交量比率", "type": "series"}]
    params = [
        {"id": "period", "name": "平均周期", "type": "int", "default": 5, "min": 1, "max": 200}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 5))

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        volume = inputs["volume"]
        period = int(params.get("period", 5))
        avg_vol = volume.rolling(window=period, min_periods=1).mean()
        return volume / avg_vol.replace(0, np.nan)


class PriceChange(FactorOperatorBase):
    operator_id = "price_change"
    name = "价格变化"
    category = "基础指标"
    description = "计算价格的变化率（收益率）"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "pct_change", "name": "变化率", "type": "series"}]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 1, "min": 1, "max": 252}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 1))

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 1))
        return price.pct_change(periods=period)


class Volatility(FactorOperatorBase):
    operator_id = "volatility"
    name = "波动率"
    category = "波动率指标"
    description = "计算收益率的标准差（波动率）"
    inputs = [{"id": "price", "name": "价格序列", "type": "series", "required": True}]
    outputs = [{"id": "volatility", "name": "波动率", "type": "series"}]
    params = [
        {"id": "period", "name": "周期", "type": "int", "default": 20, "min": 2, "max": 500},
        {"id": "annualize", "name": "年化", "type": "boolean", "default": True}
    ]
    lookback = 1

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return int(params.get("period", 20)) + 1

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        price = inputs["price"]
        period = int(params.get("period", 20))
        annualize = bool(params.get("annualize", True))
        returns = price.pct_change()
        vol = returns.rolling(window=period, min_periods=2).std()
        if annualize:
            vol = vol * np.sqrt(252)
        return vol


class ArithmeticOperator(FactorOperatorBase):
    operator_id = "arithmetic"
    name = "算术运算"
    category = "组合运算"
    description = "对两个序列进行加减乘除运算"
    inputs = [
        {"id": "left", "name": "左操作数", "type": "series", "required": True},
        {"id": "right", "name": "右操作数", "type": "series", "required": True}
    ]
    outputs = [{"id": "result", "name": "计算结果", "type": "series"}]
    params = [
        {"id": "op", "name": "运算符", "type": "select", "default": "add",
         "options": [
             {"label": "加法 (+)", "value": "add"},
             {"label": "减法 (-)", "value": "sub"},
             {"label": "乘法 (*)", "value": "mul"},
             {"label": "除法 (/)", "value": "div"}
         ]}
    ]
    lookback = 0

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return 0

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        left = inputs["left"]
        right = inputs["right"]
        op = params.get("op", "add")
        
        if op == "add":
            return left + right
        elif op == "sub":
            return left - right
        elif op == "mul":
            return left * right
        else:
            return left / right.replace(0, np.nan)


class RankNormalize(FactorOperatorBase):
    operator_id = "rank"
    name = "排序标准化"
    category = "标准化"
    description = "对截面数据进行排序并标准化到[0,1]区间"
    inputs = [{"id": "factor", "name": "因子值", "type": "series", "required": True}]
    outputs = [{"id": "ranked", "name": "排序值", "type": "series"}]
    params = [
        {"id": "method", "name": "标准化方式", "type": "select", "default": "minmax",
         "options": [
             {"label": "Min-Max", "value": "minmax"},
             {"label": "Z-Score", "value": "zscore"},
             {"label": "Rank", "value": "rank"}
         ]}
    ]
    lookback = 0

    def get_lookback(self, params: Dict[str, Any]) -> int:
        return 0

    def compute(self, inputs: Dict[str, pd.Series], params: Dict[str, Any]) -> pd.Series:
        factor = inputs["factor"]
        method = params.get("method", "minmax")
        
        if method == "minmax":
            min_val = factor.min()
            max_val = factor.max()
            range_val = max_val - min_val
            if range_val == 0:
                return pd.Series(0.5, index=factor.index)
            return (factor - min_val) / range_val
        elif method == "zscore":
            std_val = factor.std()
            if std_val == 0 or np.isnan(std_val):
                return pd.Series(0, index=factor.index)
            return (factor - factor.mean()) / std_val
        else:
            return factor.rank(pct=True)


class OperatorRegistry:
    _operators: Dict[str, FactorOperatorBase] = {}
    
    @classmethod
    def register(cls, operator: FactorOperatorBase):
        cls._operators[operator.operator_id] = operator
    
    @classmethod
    def get(cls, operator_id: str) -> Optional[FactorOperatorBase]:
        return cls._operators.get(operator_id)
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return [op.to_dict() for op in cls._operators.values()]
    
    @classmethod
    def list_by_category(cls) -> Dict[str, List[Dict[str, Any]]]:
        result = {}
        for op in cls._operators.values():
            cat = op.category
            if cat not in result:
                result[cat] = []
            result[cat].append(op.to_dict())
        return result


OperatorRegistry.register(MovingAverage())
OperatorRegistry.register(ExponentialMovingAverage())
OperatorRegistry.register(RelativeStrengthIndex())
OperatorRegistry.register(BollingerBands())
OperatorRegistry.register(Momentum())
OperatorRegistry.register(MACD())
OperatorRegistry.register(VolumeRatio())
OperatorRegistry.register(PriceChange())
OperatorRegistry.register(Volatility())
OperatorRegistry.register(ArithmeticOperator())
OperatorRegistry.register(RankNormalize())
