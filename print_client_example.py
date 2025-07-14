#!/usr/bin/env python3
"""
打印客户端示例程序
连接到发财小狗饮品店的WebSocket打印服务器，接收并处理打印任务

使用方法:
1. 确保发财小狗饮品店应用正在运行 (python app.py)
2. 运行此客户端: python print_client_example.py
3. 在管理后台确认订单时选择"启用自动打印"
4. 客户端会自动接收并处理打印任务
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PrintClient:
    """打印客户端"""
    
    def __init__(self, server_url='ws://localhost:8765', printer_name='示例打印机'):
        self.server_url = server_url
        self.printer_name = printer_name
        self.websocket = None
        self.is_connected = False
        
    async def connect(self):
        """连接到打印服务器"""
        try:
            logger.info(f"🔗 正在连接到打印服务器: {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            logger.info("✅ 连接成功！")
            
            # 发送打印机信息
            await self.send_printer_info()
            
            # 开始监听消息
            await self.listen_for_messages()
            
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            self.is_connected = False
    
    async def send_printer_info(self):
        """发送打印机信息"""
        printer_info = {
            "type": "printer_info",
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "name": self.printer_name,
                "model": "示例打印机 v1.0",
                "paper_width": 80,
                "capabilities": ["text", "qr_code", "barcode"],
                "status": "ready"
            }
        }
        
        await self.websocket.send(json.dumps(printer_info, ensure_ascii=False))
        logger.info(f"📤 已发送打印机信息: {self.printer_name}")
    
    async def listen_for_messages(self):
        """监听服务器消息"""
        logger.info("👂 开始监听打印任务...")
        
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 连接已断开")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ 监听消息时出错: {e}")
            self.is_connected = False
    
    async def handle_message(self, message):
        """处理服务器消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            logger.info(f"📨 收到消息: {msg_type}")
            
            if msg_type == 'welcome':
                logger.info(f"🎉 {data.get('message')}")
                server_info = data.get('server_info', {})
                logger.info(f"🔧 服务器: {server_info.get('name')} v{server_info.get('version')}")
                
            elif msg_type == 'new_order':
                await self.handle_new_order(data)
                
            elif msg_type == 'print_command':
                await self.handle_print_command(data)
                
            elif msg_type == 'status_request':
                await self.send_status_response()
                
            elif msg_type == 'ping':
                await self.send_pong()
                
            else:
                logger.warning(f"⚠️ 未知消息类型: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error(f"❌ 无效的JSON消息: {message}")
        except Exception as e:
            logger.error(f"❌ 处理消息时出错: {e}")
    
    async def handle_new_order(self, data):
        """处理新订单打印任务"""
        order = data.get('order', {})
        order_id = order.get('order_id')
        job_id = order.get('job_id')
        target_printer = order.get('target_printer', {})
        
        logger.info(f"🆕 收到新订单打印任务:")
        logger.info(f"   订单号: #{order_id}")
        logger.info(f"   任务ID: {job_id}")
        logger.info(f"   目标打印机: {target_printer.get('name', '默认')}")
        
        # 显示打印内容
        print("\n" + "="*50)
        print("📄 打印内容:")
        print("="*50)
        print(order.get('content', ''))
        print("="*50)
        
        # 模拟打印过程
        await self.simulate_printing(order)
    
    async def handle_print_command(self, data):
        """处理打印命令"""
        print_data = data.get('data', {})
        logger.info(f"🖨️ 收到打印命令: {print_data.get('type', 'unknown')}")
        
        if 'content' in print_data:
            print("\n" + "="*50)
            print("📄 打印内容:")
            print("="*50)
            print(print_data['content'])
            print("="*50)
        
        # 模拟打印过程
        await self.simulate_printing(print_data)
    
    async def simulate_printing(self, print_data):
        """模拟打印过程"""
        job_id = print_data.get('job_id')
        
        # 发送开始打印状态
        if job_id:
            await self.send_print_status(job_id, 'printing', '开始打印')
        
        logger.info("🖨️ 正在打印...")
        
        # 模拟打印时间（2秒）
        await asyncio.sleep(2)
        
        # 这里可以添加实际的打印机驱动代码
        # 例如：
        # - 发送到热敏打印机
        # - 调用系统打印服务
        # - 保存为PDF文件
        # - 发送到网络打印机等
        
        # 模拟打印结果（90%成功率）
        import random
        success = random.random() > 0.1
        
        if success:
            logger.info("✅ 打印完成")
            if job_id:
                await self.send_print_status(job_id, 'completed', '打印成功')
        else:
            logger.error("❌ 打印失败")
            if job_id:
                await self.send_print_status(job_id, 'failed', '打印机缺纸')
    
    async def send_print_status(self, job_id, status, message):
        """发送打印状态"""
        status_msg = {
            "type": "print_status",
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "status": status,
            "message": message
        }
        
        await self.websocket.send(json.dumps(status_msg, ensure_ascii=False))
        logger.info(f"📤 已发送状态: {status} - {message}")
    
    async def send_status_response(self):
        """发送状态响应"""
        status_response = {
            "type": "status_response",
            "timestamp": datetime.now().isoformat(),
            "printer_status": {
                "status": "ready",
                "paper_level": "normal",
                "ink_level": "high",
                "temperature": "normal",
                "last_print": datetime.now().isoformat()
            }
        }
        
        await self.websocket.send(json.dumps(status_response, ensure_ascii=False))
        logger.info("📤 已发送状态响应")
    
    async def send_pong(self):
        """发送心跳响应"""
        pong_msg = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(pong_msg))
        logger.info("💓 发送心跳响应")

async def main():
    """主函数"""
    print("🖨️ 发财小狗饮品店 - 打印客户端示例")
    print("=" * 50)
    print("📋 功能说明:")
    print("1. 连接到WebSocket打印服务器")
    print("2. 接收订单打印任务")
    print("3. 模拟打印过程")
    print("4. 反馈打印状态")
    print("=" * 50)
    
    # 创建打印客户端
    client = PrintClient()
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 客户端异常: {e}")

if __name__ == '__main__':
    print("🚀 启动打印客户端...")
    print("💡 提示: 按 Ctrl+C 退出程序")
    print()
    
    # 运行客户端
    asyncio.run(main())
