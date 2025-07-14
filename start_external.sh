#!/bin/bash
echo "========================================"
echo "发财小狗饮品店 - 外网调试启动脚本"
echo "========================================"
echo

echo "🚀 启动Flask应用..."
python run.py --host=0.0.0.0 --port=5000 &
FLASK_PID=$!

echo "⏳ 等待Flask应用启动..."
sleep 5

echo "🌐 启动ngrok隧道..."
./ngrok http 5000

# 清理
kill $FLASK_PID 2>/dev/null
