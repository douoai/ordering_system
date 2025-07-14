@echo off
echo ========================================
echo 发财小狗饮品店 - 外网调试启动脚本
echo ========================================
echo.

echo 🚀 启动Flask应用...
start "Flask App" cmd /k "python run.py --host=0.0.0.0 --port=5000"

echo ⏳ 等待Flask应用启动...
timeout /t 5 /nobreak > nul

echo 🌐 启动ngrok隧道...
ngrok.exe http 5000

pause
