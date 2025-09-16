#!/bin/bash

# 设置UTF-8编码环境
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# 查找并终止在8001和8012端口上运行的进程
echo "正在停止旧的服务..."
kill -9 $(lsof -t -i:8001) 2>/dev/null
kill -9 $(lsof -t -i:8012) 2>/dev/null

# 启动后端服务
echo "正在启动后端服务..."
cd backend
PYTHONIOENCODING=utf-8 python3 app.py &
cd ..

# 启动前端服务
echo "正在启动前端服务..."
cd frontend
npm start &
cd ..

echo "服务已启动！"
