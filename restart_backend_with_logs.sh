#!/bin/bash

# 重启后端并持续监控日志的脚本

# 设置UTF-8编码环境
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

PORT=8012

echo "🔄 正在检查端口 $PORT 上的进程..."

# 查找占用目标端口的进程
PID=$(lsof -t -i:$PORT)

if [ ! -z "$PID" ]; then
    echo "🛑 发现端口 $PORT 被进程 $PID 占用，正在强制停止..."
    kill -9 $PID
    sleep 1
    echo "✅ 进程已停止"
else
    echo "✅ 端口 $PORT 空闲"
fi

# 额外停止所有可能的 python app.py 进程
echo "🔄 停止所有 python app.py 进程..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1

echo "📁 切换到后端目录..."
cd "$(dirname "$0")/backend"

echo "🚀 启动Flask后端服务..."
echo "📡 服务地址: http://localhost:$PORT"
echo "🔍 实时监控日志输出..."
echo "按 Ctrl+C 停止服务"
echo "============================================================"

# 启动后端服务，所有输出直接显示到终端
PYTHONIOENCODING=utf-8 python3 -u app.py --debug