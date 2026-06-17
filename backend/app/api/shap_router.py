from fastapi import APIRouter, HTTPException, Response
from typing import Optional
import logging
import json

from app.core.shap_engine import shap_analyzer
from app.models.schemas import ShapRequest, ShapResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shap", tags=["shap"])


@router.post("/analyze", response_model=ShapResult)
def analyze_shap(request: ShapRequest):
    try:
        result = shap_analyzer.compute_shap(
            factor_name=request.factor_name,
            factor_values=request.factor_values,
            dataset_name=request.dataset_name,
            n_samples=request.n_samples,
            target_period=request.target_period
        )
        return ShapResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"SHAP analysis error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"SHAP分析失败: {str(e)}")


@router.post("/report")
def generate_pdf_report(
    factor_name: str,
    shap_result: dict,
    backtest_result: Optional[dict] = None
):
    try:
        pdf_bytes = shap_analyzer.generate_pdf_report(
            shap_result=shap_result,
            factor_name=factor_name,
            backtest_result=backtest_result
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=SHAP_Report_{factor_name}.pdf"}
        )
    except Exception as e:
        import traceback
        logger.error(f"PDF generation error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"PDF生成失败: {str(e)}")
