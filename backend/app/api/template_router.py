from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from app.core.template_market import template_market
from app.models.schemas import (
    TemplatePublishRequest, FactorTemplate,
    TemplateListResponse, TemplateForkResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 50
):
    try:
        templates, total = template_market.list_templates(
            category=category, search=search,
            sort_by=sort_by, sort_order=sort_order,
            offset=offset, limit=limit
        )
        return TemplateListResponse(
            success=True,
            message=f"共 {total} 个模板",
            total=total,
            templates=templates
        )
    except Exception as e:
        import traceback
        logger.error(f"List templates error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@router.get("/categories")
def list_categories():
    return {
        "success": True,
        "categories": template_market.get_categories()
    }


@router.get("/{template_id}")
def get_template(template_id: str):
    template = template_market.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "template": template}


@router.post("/publish", response_model=FactorTemplate)
def publish_template(request: TemplatePublishRequest):
    try:
        template_id = template_market.publish_template(
            name=request.name,
            description=request.description,
            category=request.category,
            tags=request.tags,
            author_name=request.author_name,
            workflow=request.workflow.model_dump(),
            factor_stats=request.factor_stats,
            backtest_result=request.backtest_result,
            is_public=request.is_public
        )
        template = template_market.get_template(template_id, increment_views=False)
        if not template:
            raise HTTPException(status_code=404, detail="创建后模板未找到")
        return FactorTemplate(**template)
    except Exception as e:
        import traceback
        logger.error(f"Publish template error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"发布模板失败: {str(e)}")


@router.post("/{template_id}/fork", response_model=TemplateForkResponse)
def fork_template(template_id: str, author_name: str = Query(..., description="新作者名称"), new_name: Optional[str] = None):
    result = template_market.fork_template(template_id, author_name, new_name)
    if not result:
        raise HTTPException(status_code=404, detail="模板不存在")
    new_id, workflow = result
    return TemplateForkResponse(
        success=True,
        message=f"成功Fork模板，新模板ID: {new_id}",
        new_template_id=new_id,
        workflow=workflow
    )


@router.post("/{template_id}/like")
def like_template(template_id: str):
    success = template_market.like_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "message": "点赞成功"}


@router.delete("/{template_id}")
def delete_template(template_id: str):
    success = template_market.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "message": "删除成功"}


@router.post("/{template_id}/apply")
def apply_template(template_id: str):
    template = template_market.get_template(template_id, increment_views=True)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {
        "success": True,
        "message": "模板已加载到工作流",
        "workflow": template["workflow"],
        "name": template["name"],
        "description": template["description"],
        "factor_stats": template.get("factor_stats"),
        "backtest_result": template.get("backtest_result")
    }
