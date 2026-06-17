@echo off
echo ========================================
echo   Stock Factor Workbench - 后端启动
echo ========================================
cd backend

if not exist venv (
    echo [1/2] 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/2] 安装依赖...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo 启动FastAPI服务: http://localhost:8000
echo Swagger文档: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
