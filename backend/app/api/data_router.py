from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import date
import json

from app.core.duckdb_engine import duckdb_engine
from app.core.cache import cache_manager, cached
from app.models.schemas import (
    DataImportResponse, DatasetInfo, Frequency
)

router = APIRouter(prefix="/api/data", tags=["数据管理"])


@router.post("/import", response_model=DataImportResponse)
async def import_data(
    file: UploadFile = File(...),
    file_type: str = Query("csv", description="文件类型: csv 或 parquet"),
    frequency: Frequency = Query(Frequency.DAILY, description="数据频率")
):
    try:
        content = await file.read()
        result = duckdb_engine.import_file(
            file_content=content,
            file_type=file_type,
            frequency=frequency.value
        )
        cache_manager.clear_pattern("factor_workbench:data:*")
        return DataImportResponse(
            success=True,
            message=f"数据导入成功: {result['row_count']} 行",
            **result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/datasets")
@cached(prefix="data:datasets", ttl=60)
def list_datasets():
    tables = duckdb_engine.list_tables()
    result = []
    for t in tables:
        info = duckdb_engine.get_table_info(t["name"])
        if info:
            info["frequency"] = Frequency.DAILY
            result.append(info)
    return result


@router.get("/datasets/{dataset_name}")
def get_dataset_info(dataset_name: str):
    info = duckdb_engine.get_table_info(dataset_name)
    if not info:
        raise HTTPException(status_code=404, detail="数据集不存在")
    info["frequency"] = Frequency.DAILY
    return info


@router.delete("/datasets/{dataset_name}")
def delete_dataset(dataset_name: str):
    success = duckdb_engine.delete_table(dataset_name)
    cache_manager.clear_pattern("factor_workbench:data:*")
    if success:
        return {"success": True, "message": f"数据集 {dataset_name} 已删除"}
    raise HTTPException(status_code=500, detail="删除失败")


@router.get("/datasets/{dataset_name}/preview")
def preview_dataset(
    dataset_name: str,
    limit: int = Query(100, ge=1, le=10000)
):
    info = duckdb_engine.get_table_info(dataset_name)
    if not info:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    df = duckdb_engine.query_data(dataset_name, limit=limit)
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            if hasattr(val, 'isoformat'):
                record[col] = val.isoformat()
            else:
                record[col] = val
        records.append(record)
    return {
        "columns": list(df.columns),
        "data": records,
        "total": info["row_count"]
    }


@router.get("/datasets/{dataset_name}/stocks")
def list_stocks(
    dataset_name: str,
    limit: int = Query(500, ge=1, le=10000)
):
    codes = duckdb_engine.get_stock_codes(dataset_name, limit=limit)
    return {"stocks": codes, "count": len(codes)}


@router.post("/generate-sample")
def generate_sample_data(
    n_stocks: int = Query(50, ge=5, le=500, description="股票数量"),
    n_days: int = Query(252, ge=20, le=2520, description="交易日数量"),
    dataset_name: Optional[str] = Query(None, description="数据集名称")
):
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        np.random.seed(42)
        end_date = datetime.now() - timedelta(days=1)
        dates = []
        current = end_date - timedelta(days=n_days * 2)
        while len(dates) < n_days:
            if current.weekday() < 5:
                dates.append(current)
            current += timedelta(days=1)
        dates = sorted(dates)
        
        records = []
        stock_codes = [f"{600000 + i:06d}.SH" for i in range(n_stocks)] + [f"{300000 + i:06d}.SZ" for i in range(n_stocks // 2)]
        stock_codes = stock_codes[:n_stocks]
        
        for code in stock_codes:
            base_price = np.random.uniform(10, 100)
            price = base_price
            for dt in dates:
                ret = np.random.normal(0.0005, 0.02)
                open_p = price * (1 + np.random.normal(0, 0.005))
                close_p = price * (1 + ret)
                high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, 0.01)))
                low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, 0.01)))
                volume = np.random.randint(100000, 10000000)
                amount = volume * close_p
                
                records.append({
                    "ts_code": code,
                    "trade_date": dt.date(),
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(close_p, 2),
                    "volume": volume,
                    "amount": round(amount, 2)
                })
                price = close_p
        
        df = pd.DataFrame(records)
        
        if dataset_name is None:
            dataset_name = f"sample_data_{n_stocks}stocks_{n_days}days"
        
        table_name = dataset_name.replace(" ", "_").replace("-", "_")
        
        with duckdb_engine.connection() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        cache_manager.clear_pattern("factor_workbench:data:*")
        
        return DataImportResponse(
            success=True,
            message=f"示例数据生成成功: {n_stocks} 只股票 × {n_days} 天 = {row_count} 行",
            table_name=table_name,
            row_count=row_count,
            columns=list(df.columns)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
