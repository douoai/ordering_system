#!/usr/bin/env python3
"""
简化版打印客户端
用于对接发财小狗饮品店的打印系统

使用方法:
1. 修改下面的配置参数
2. 运行: python simple_print_client.py
3. 在管理后台确认订单时选择"启用自动打印"
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

# ==================== 配置参数 ====================
SERVER_URL = 'ws://localhost:8765'  # WebSocket服务器地址
PRINTER_NAME = '我的打印机'           # 打印机名称
PRINTER_MODEL = 'TP-80'             # 打印机型号
AUTO_PRINT = True                   # 是否自动打印（False则只显示内容）

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplePrintClient:
    """简化版打印客户端"""
    
    def __init__(self):
        self.server_url = SERVER_URL
        self.printer_name = PRINTER_NAME
        self.printer_model = PRINTER_MODEL
        self.auto_print = AUTO_PRINT
        
    async def start(self):
        """启动客户端"""
        logger.info(f"🚀 启动打印客户端: {self.printer_name}")
        logger.info(f"🔗 连接服务器: {self.server_url}")
        
        while True:
            try:
                await self.connect_and_listen()
            except Exception as e:
                logger.error(f"❌ 连接异常: {e}")
                logger.info("⏳ 5秒后重新连接...")
                await asyncio.sleep(5)
    
    async def connect_and_listen(self):
        """连接并监听消息"""
        async with websockets.connect(self.server_url) as websocket:
            logger.info("✅ 连接成功")
            
            # 发送打印机信息
            await self.register_printer(websocket)
            
            # 监听消息
            async for message in websocket:
                await self.handle_message(websocket, message)
    
    async def register_printer(self, websocket):
        """注册打印机信息"""
        printer_info = {
            "type": "printer_info",
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "name": self.printer_name,
                "model": self.printer_model,
                "status": "ready",
                "capabilities": ["text", "receipt"]
            }
        }
        
        await websocket.send(json.dumps(printer_info, ensure_ascii=False))
        logger.info(f"📤 已注册打印机: {self.printer_name}")
    
    async def handle_message(self, websocket, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'welcome':
                logger.info(f"🎉 {data.get('message', '连接成功')}")
                
            elif msg_type == 'new_order':
                await self.process_print_job(websocket, data['order'])
                
            elif msg_type == 'print_command':
                await self.process_print_job(websocket, data['data'])
                
            elif msg_type == 'ping':
                # 响应心跳
                pong = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(pong))
                
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
    
    async def process_print_job(self, websocket, job_data):
        """处理打印任务"""
        order_id = job_data.get('order_id', 'Unknown')
        job_id = job_data.get('job_id')
        content = job_data.get('content', '')
        target_printer = job_data.get('target_printer', {})
        
        logger.info(f"📋 收到打印任务:")
        logger.info(f"   订单号: #{order_id}")
        logger.info(f"   目标打印机: {target_printer.get('name', '默认')}")
        
        # 显示打印内容
        print("\n" + "="*60)
        print("📄 订单内容:")
        print("="*60)
        print(content)
        print("="*60)
        
        # 执行打印
        if self.auto_print:
            success = await self.execute_print(content)
        else:
            logger.info("ℹ️ 自动打印已禁用，仅显示内容")
            success = True
        
        # 发送打印状态
        if job_id:
            await self.send_print_status(
                websocket, 
                job_id, 
                'completed' if success else 'failed',
                '打印成功' if success else '打印失败'
            )
    
    async def execute_print(self, content):
        """执行实际打印"""
        try:
            logger.info("🖨️ 开始打印...")
            
            # ==================== 在这里添加您的打印逻辑 ====================
            # 示例1: 保存为文件
            # with open(f'print_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'w', encoding='utf-8') as f:
            #     f.write(content)
            
            # 示例2: 发送到网络打印机
            # import socket
            # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # sock.connect(('192.168.1.100', 9100))
            # sock.send(content.encode('utf-8'))
            # sock.close()
            
            # 示例3: 调用系统打印命令
            # import subprocess
            # subprocess.run(['lp', '-d', 'printer_name'], input=content.encode('utf-8'))
            
            # 示例4: 使用Python打印库
            # from escpos.printer import Network
            # p = Network("192.168.1.100")
            # p.text(content)
            # p.cut()
            # p.close()
            
            # 当前为模拟打印（延迟2秒）
            await asyncio.sleep(2)
            # ================================================================
            
            logger.info("✅ 打印完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 打印失败: {e}")
            return False
    
    async def send_print_status(self, websocket, job_id, status, message):
        """发送打印状态"""
        status_msg = {
            "type": "print_status",
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "status": status,
            "message": message
        }
        
        await websocket.send(json.dumps(status_msg, ensure_ascii=False))
        logger.info(f"📤 状态反馈: {status} - {message}")

def main():
    """主函数"""
    print("🖨️ 发财小狗饮品店 - 简化版打印客户端")
    print("=" * 60)
    print(f"📋 配置信息:")
    print(f"   服务器地址: {SERVER_URL}")
    print(f"   打印机名称: {PRINTER_NAME}")
    print(f"   打印机型号: {PRINTER_MODEL}")
    print(f"   自动打印: {'是' if AUTO_PRINT else '否（仅显示）'}")
    print("=" * 60)
    print("💡 提示:")
    print("   1. 确保发财小狗饮品店应用正在运行")
    print("   2. 在管理后台确认订单时选择'启用自动打印'")
    print("   3. 按 Ctrl+C 退出程序")
    print("=" * 60)
    print()
    
    # 启动客户端
    client = SimplePrintClient()
    
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("\n⏹️ 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")

if __name__ == '__main__':
    main()
