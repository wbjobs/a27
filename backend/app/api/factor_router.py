from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import date

from app.core.operators import OperatorRegistry
from app.core.factor_engine import factor_executor
from app.core.cache import cache_manager, cached
from app.core.correlation_engine import factor_correlation_analyzer
from app.models.schemas import (
    FactorComputeRequest, FactorComputeResponse, FactorOperator,
    FactorCorrelationRequest, FactorCorrelationResult
)

router = APIRouter(prefix="/api/factor", tags=["因子计算"])


@router.get("/operators")
@cached(prefix="factor:operators", ttl=3600)
def list_operators():
    return {
        "total": len(OperatorRegistry.list_all()),
        "by_category": OperatorRegistry.list_by_category(),
        "operators": OperatorRegistry.list_all()
    }


@router.get("/operators/{operator_id}", response_model=FactorOperator)
def get_operator(operator_id: str):
    op = OperatorRegistry.get(operator_id)
    if not op:
        raise HTTPException(status_code=404, detail=f"算子 {operator_id} 不存在")
    return op.to_dict()


@router.post("/compute", response_model=FactorComputeResponse)
def compute_factor(request: FactorComputeRequest):
    try:
        cache_key = cache_manager._make_key(
            "factor:compute",
            request.model_dump_json()
        )
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return FactorComputeResponse(
                success=True,
                message="使用缓存结果",
                **cached_result
            )
        
        factor_values, stats = factor_executor.execute_workflow(
            workflow=request.workflow,
            dataset_name=request.dataset_name,
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date,
            forward_validation=request.forward_validation
        )
        
        result = {
            "factor_values": factor_values,
            "stats": stats
        }
        
        if request.forward_validation and "forward_validation" in stats:
            result["forward_validation"] = stats.pop("forward_validation")
        cache_manager.set(cache_key, result, ttl=7200)
        
        return FactorComputeResponse(
            success=True,
            message=f"因子计算完成: {stats.get('count', 0)} 条记录",
            factor_values=factor_values,
            stats=stats
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.post("/validate-workflow")
def validate_workflow(workflow: Dict[str, Any]):
    try:
        from app.models.schemas import FactorWorkflow
        wf = FactorWorkflow(**workflow)
        
        node_ids = {n.id for n in wf.nodes}
        if wf.output_node not in node_ids:
            raise ValueError(f"输出节点 {wf.output_node} 不存在")
        
        for node in wf.nodes:
            op = OperatorRegistry.get(node.operator_id)
            if not op:
                raise ValueError(f"节点 {node.id} 使用了未知算子: {node.operator_id}")
            
            for input_id, source in node.inputs.items():
                if not source:
                    continue
                if source.startswith("market:"):
                    continue
                source_node = source.split(":")[0] if ":" in source else source
                if source_node not in node_ids:
                    raise ValueError(f"节点 {node.id} 的输入 {input_id} 引用了不存在的节点 {source_node}")
        
        from app.core.factor_engine import FactorWorkflowExecutor
        executor = FactorWorkflowExecutor()
        order = executor._topological_sort(wf.nodes)
        
        return {
            "valid": True,
            "execution_order": order,
            "message": "工作流验证通过"
        }
    except ValueError as e:
        return {"valid": False, "message": str(e)}
    except Exception as e:
        return {"valid": False, "message": f"验证失败: {str(e)}"}


@router.post("/correlation", response_model=FactorCorrelationResult)
def analyze_factor_correlation(request: FactorCorrelationRequest):
    try:
        result = factor_correlation_analyzer.analyze(
            factor_values_list=request.factor_values_list,
            vif_threshold=request.vif_threshold,
            corr_threshold=request.corr_threshold
        )
        return FactorCorrelationResult(**result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"相关性分析失败: {str(e)}")
