#!/bin/bash

# 停止 SMS Viewer 服务

echo "🛑 停止 SMS Viewer 服务..."

# 停止后端 (Python Flask on port 5001)
BACKEND_PIDS=$(lsof -ti:5001 2>/dev/null)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "   停止后端 (端口 5001)..."
    kill $BACKEND_PIDS 2>/dev/null
    echo "   ✅ 后端已停止"
else
    echo "   后端未运行"
fi

# 停止前端 (Vite on port 5173)
FRONTEND_PIDS=$(lsof -ti:5173 2>/dev/null)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "   停止前端 (端口 5173)..."
    kill $FRONTEND_PIDS 2>/dev/null
    echo "   ✅ 前端已停止"
else
    echo "   前端未运行"
fi

echo ""
echo "✅ 完成"
