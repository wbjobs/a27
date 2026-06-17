@echo off
echo ========================================
echo   Stock Factor Workbench - 前端启动
echo ========================================
cd frontend

if not exist node_modules (
    echo [1/1] 安装依赖...
    npm install
)

echo.
echo 启动Vite开发服务器: http://localhost:5173
echo.
npm run dev

pause
