#!/bin/bash

# SMS Viewer 启动脚本
# 同时启动后端 API 和前端开发服务器

echo "========================================"
echo "  📱 SMS Viewer 启动脚本"
echo "========================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3"
    exit 1
fi

# 检查 Node.js
if ! command -v npm &> /dev/null; then
    echo "❌ 未找到 npm"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 清理函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    
    # 停止后端
    lsof -ti:5001 | xargs kill 2>/dev/null
    echo "   后端已停止"
    
    # 停止前端
    lsof -ti:5173 | xargs kill 2>/dev/null
    echo "   前端已停止"
    
    echo "✅ 服务已停止"
    exit 0
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

# 启动后端
echo ""
echo "🚀 启动后端 API (端口 5001)..."
python3 api_server.py > /tmp/sms_api.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动 (最多等待 15 秒)
echo "   等待后端启动..."
for i in {1..15}; do
    if lsof -ti:5001 > /dev/null 2>&1; then
        echo "   ✅ 后端已启动"
        break
    fi
    sleep 1
    if [ $i -eq 15 ]; then
        echo "   ❌ 后端启动超时"
        echo "   查看日志: cat /tmp/sms_api.log"
        exit 1
    fi
done

# 启动前端
echo ""
echo "🚀 启动前端 (端口 5173)..."
cd frontend
npm run dev > /tmp/sms_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# 等待前端启动 (最多等待 20 秒)
echo "   等待前端启动..."
for i in {1..20}; do
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo "   ✅ 前端已启动"
        break
    fi
    sleep 1
    if [ $i -eq 20 ]; then
        echo "   ❌ 前端启动超时"
        echo "   查看日志: cat /tmp/sms_frontend.log"
        lsof -ti:5001 | xargs kill 2>/dev/null
        exit 1
    fi
done

echo ""
echo "========================================"
echo "✅ 服务已启动"
echo ""
echo "  🌐 前端: http://localhost:5173"
echo "  🔌 API:  http://localhost:5001"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================"

# 保持脚本运行
while true; do
    sleep 1
done
