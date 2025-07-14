@echo off
chcp 65001 >nul
title 发财小狗饮品店 - 外网访问启动器

echo ========================================
echo 🐕 发财小狗饮品店 - 外网访问启动器
echo ========================================
echo.

echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python并添加到系统PATH
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo 🔧 配置防火墙规则...
netsh advfirewall firewall add rule name="Flask App Port 5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  防火墙配置失败，可能需要管理员权限
) else (
    echo ✅ 防火墙规则配置成功
)

echo.
echo 🚀 启动Flask应用...
start "Flask App" cmd /k "python app.py"

echo ⏳ 等待应用启动...
timeout /t 5 /nobreak >nul

echo.
echo 🌐 获取网络信息...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
    set "ip=%%i"
    goto :found
)
:found
set "ip=%ip: =%"

echo.
echo ========================================
echo 🎉 外网访问已就绪！
echo ========================================
echo.
echo 📍 访问地址:
echo 本地访问: http://localhost:5000
echo 局域网访问: http://%ip%:5000
echo.
echo 🌐 页面链接:
echo Bootstrap首页: http://%ip%:5000/
echo Element UI首页: http://%ip%:5000/?ui=element
echo 管理后台: http://%ip%:5000/admin/
echo Element UI管理后台: http://%ip%:5000/admin/?ui=element
echo.
echo 📱 移动设备访问:
echo 1. 确保手机和电脑在同一WiFi网络
echo 2. 在手机浏览器输入: http://%ip%:5000
echo 3. 即可访问您的饮品店应用
echo.
echo 🔧 如果无法访问:
echo 1. 检查防火墙设置，允许端口5000
echo 2. 确保设备在同一网络
echo 3. 尝试关闭Windows防火墙（临时）
echo.
echo ⚠️  注意事项:
echo - 此方法适用于局域网访问
echo - 如需真正的外网访问，建议使用云服务器
echo - 或使用内网穿透工具如ngrok、花生壳等
echo.
echo 🔄 应用正在运行中...
echo 关闭此窗口将停止应用
echo.

pause
