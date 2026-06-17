from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.core.duckdb_engine import duckdb_engine
from app.api.data_router import router as data_router
from app.api.factor_router import router as factor_router
from app.api.backtest_router import router as backtest_router
from app.api.portfolio_router import router as portfolio_router
from app.api.shap_router import router as shap_router
from app.api.template_router import router as template_router
from app.api.ws_router import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    duckdb_engine.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="基于DuckDB + Observable的交互式股票因子挖掘工作台",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)
app.include_router(factor_router)
app.include_router(backtest_router)
app.include_router(portfolio_router)
app.include_router(shap_router)
app.include_router(template_router)
app.include_router(ws_router, prefix="/ws")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "running",
        "redis_enabled": settings.redis_enabled,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    status = {"status": "healthy", "duckdb": "ok"}
    from app.core.cache import cache_manager
    status["redis"] = "ok" if cache_manager.is_available else "unavailable"
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
