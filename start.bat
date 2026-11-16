@echo off
chcp 65001 >nul
echo ============================================
echo   拾光叙 · 城市人文漫步 RAG 助手 启动中
echo ============================================

if not exist "%~dp0frontend\node_modules" (
  echo [1/2] 首次运行，安装前端依赖（需要联网，约 1-2 分钟）...
  pushd "%~dp0frontend"
  call npm install
  popd
)

echo [2/2] 启动服务...
start "拾光叙-后端" cmd /k "cd /d %~dp0backend && python run.py"
timeout /t 3 /nobreak >nul
start "拾光叙-前端" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 后端 http://127.0.0.1:8000/docs
echo 前端 http://localhost:5173
echo 离线演示：直接双击「拾光叙-海报网页.html」
pause
