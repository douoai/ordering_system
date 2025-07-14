@echo off
echo ========================================
echo 发财小狗饮品店 - 启动外网隧道
echo ========================================
echo.

echo 🌐 正在启动ngrok隧道...
echo 📍 本地地址: http://localhost:5000
echo ⏳ 请稍等，正在建立外网连接...
echo.

ngrok.exe http 5000

pause
