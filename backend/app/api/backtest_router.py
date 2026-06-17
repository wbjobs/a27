from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from app.core.backtest_engine import backtest_engine
from app.core.cache import cache_manager, cached
from app.models.schemas import BacktestRequest, BacktestResult

router = APIRouter(prefix="/api/backtest", tags=["因子回测"])


@router.post("/run", response_model=BacktestResult)
def run_backtest(request: BacktestRequest):
    try:
        cache_key = cache_manager._make_key(
            "backtest:run",
            request.factor_name,
            request.dataset_name,
            request.n_groups,
            request.holding_period,
            request.commission_rate,
            str(request.start_date) if request.start_date else "",
            str(request.end_date) if request.end_date else "",
            len(request.factor_values)
        )
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            if isinstance(cached_result, dict):
                cached_result["message"] = "使用缓存结果"
                return BacktestResult(**cached_result)
        
        result = backtest_engine.run_backtest(request)
        
        if result.success:
            cache_manager.set(cache_key, result.model_dump(), ttl=14400)
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")


@router.post("/quick-analysis")
def quick_analysis(data: Dict[str, Any]):
    try:
        import pandas as pd
        import numpy as np
        from scipy import stats
        
        factor_values = data.get("factor_values", [])
        if not factor_values:
            raise ValueError("缺少因子值数据")
        
        df = pd.DataFrame(factor_values)
        if "factor_value" not in df.columns:
            raise ValueError("factor_value 列不存在")
        
        vals = df["factor_value"].dropna()
        
        percentiles = {}
        for p in [5, 10, 25, 50, 75, 90, 95]:
            percentiles[str(p)] = float(np.percentile(vals, p))
        
        hist, bin_edges = np.histogram(vals, bins=50)
        
        return {
            "success": True,
            "statistics": {
                "count": int(len(vals)),
                "mean": float(vals.mean()),
                "std": float(vals.std()),
                "skew": float(stats.skew(vals)) if len(vals) > 2 else 0,
                "kurtosis": float(stats.kurtosis(vals)) if len(vals) > 3 else 0,
                "min": float(vals.min()),
                "max": float(vals.max()),
                "percentiles": percentiles
            },
            "distribution": {
                "histogram": hist.tolist(),
                "bin_edges": bin_edges.tolist()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
