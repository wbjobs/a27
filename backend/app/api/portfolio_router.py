from fastapi import APIRouter, HTTPException, Body
from typing import Optional
import logging

from app.core.portfolio_engine import portfolio_optimizer
from app.models.schemas import PortfolioRequest, PortfolioResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.post("/optimize", response_model=PortfolioResult)
def optimize_portfolio(request: PortfolioRequest):
    try:
        factors = [f.model_dump() for f in request.factors]
        result = portfolio_optimizer.optimize({
            "dataset_name": request.dataset_name,
            "factors": factors,
            "model": request.model.value,
            "risk_free_rate": request.risk_free_rate,
            "target_return": request.target_return,
            "min_weight": request.min_weight,
            "max_weight": request.max_weight,
            "rebalance_freq": request.rebalance_freq
        })
        return PortfolioResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Portfolio optimization error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"优化失败: {str(e)}")


@router.get("/models")
def list_optimization_models():
    return {
        "success": True,
        "models": [
            {"id": "mean_variance", "name": "均值-方差模型", "description": "Markowitz经典均值方差优化，最大化夏普比率"},
            {"id": "min_variance", "name": "最小方差模型", "description": "追求风险最小化的保守策略"},
            {"id": "max_sharpe", "name": "最大夏普比率模型", "description": "最大化收益风险比"},
            {"id": "risk_parity", "name": "风险平价模型", "description": "各因子贡献相等风险，桥水全天候策略"},
            {"id": "equal_weight", "name": "等权重模型", "description": "简单等权分配，作为基准对比"}
        ]
    }
