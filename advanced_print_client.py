#!/usr/bin/env python3
"""
高级版打印客户端
支持配置文件、多种打印方式、错误处理和重连机制

使用方法:
1. 修改 print_client_config.json 配置文件
2. 安装依赖: pip install websockets python-escpos
3. 运行: python advanced_print_client.py
"""

import asyncio
import websockets
import json
import logging
import os
import socket
import subprocess
from datetime import datetime
from pathlib import Path

class AdvancedPrintClient:
    """高级版打印客户端"""
    
    def __init__(self, config_file='print_client_config.json'):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 配置文件 {config_file} 不存在")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式错误: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            "server": {"url": "ws://localhost:8765", "reconnect_interval": 5},
            "printer": {"name": "默认打印机", "model": "Generic"},
            "settings": {"auto_print": True, "log_level": "INFO"},
            "print_methods": {"method": "file"}
        }
    
    def setup_logging(self):
        """设置日志"""
        log_level = self.config.get('settings', {}).get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('print_client.log', encoding='utf-8')
            ]
        )
    
    async def start(self):
        """启动客户端"""
        self.logger.info("🚀 启动高级版打印客户端")
        self.logger.info(f"📋 打印机: {self.config['printer']['name']}")
        self.logger.info(f"🔗 服务器: {self.config['server']['url']}")
        
        while True:
            try:
                await self.connect_and_listen()
            except Exception as e:
                self.logger.error(f"❌ 连接异常: {e}")
                interval = self.config['server'].get('reconnect_interval', 5)
                self.logger.info(f"⏳ {interval}秒后重新连接...")
                await asyncio.sleep(interval)
    
    async def connect_and_listen(self):
        """连接并监听消息"""
        server_url = self.config['server']['url']
        
        async with websockets.connect(server_url) as websocket:
            self.logger.info("✅ 连接成功")
            
            # 注册打印机
            await self.register_printer(websocket)
            
            # 监听消息
            async for message in websocket:
                await self.handle_message(websocket, message)
    
    async def register_printer(self, websocket):
        """注册打印机信息"""
        printer_config = self.config['printer']
        
        printer_info = {
            "type": "printer_info",
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "name": printer_config.get('name', '未知打印机'),
                "model": printer_config.get('model', 'Generic'),
                "type": printer_config.get('type', 'thermal'),
                "paper_width": printer_config.get('paper_width', 80),
                "ip_address": printer_config.get('ip_address'),
                "status": "ready",
                "capabilities": ["text", "receipt", "qr_code"]
            }
        }
        
        await websocket.send(json.dumps(printer_info, ensure_ascii=False))
        self.logger.info(f"📤 已注册打印机: {printer_config['name']}")
    
    async def handle_message(self, websocket, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'welcome':
                self.logger.info(f"🎉 {data.get('message', '连接成功')}")
                
            elif msg_type == 'new_order':
                await self.process_print_job(websocket, data['order'])
                
            elif msg_type == 'print_command':
                await self.process_print_job(websocket, data['data'])
                
            elif msg_type == 'ping':
                await self.send_pong(websocket)
                
        except Exception as e:
            self.logger.error(f"❌ 处理消息失败: {e}")
    
    async def process_print_job(self, websocket, job_data):
        """处理打印任务"""
        order_id = job_data.get('order_id', 'Unknown')
        job_id = job_data.get('job_id')
        content = job_data.get('content', '')
        target_printer = job_data.get('target_printer', {})
        
        self.logger.info(f"📋 收到打印任务 #{order_id}")
        self.logger.info(f"🎯 目标打印机: {target_printer.get('name', '默认')}")
        
        # 显示内容
        print(f"\n{'='*60}")
        print(f"📄 订单 #{order_id} 打印内容:")
        print(f"{'='*60}")
        print(content)
        print(f"{'='*60}\n")
        
        # 执行打印
        success = False
        error_message = ""
        
        if self.config['settings'].get('auto_print', True):
            try:
                success = await self.execute_print(content, order_id)
            except Exception as e:
                error_message = str(e)
                self.logger.error(f"❌ 打印失败: {e}")
        else:
            self.logger.info("ℹ️ 自动打印已禁用")
            success = True
        
        # 发送状态反馈
        if job_id:
            status = 'completed' if success else 'failed'
            message = '打印成功' if success else f'打印失败: {error_message}'
            await self.send_print_status(websocket, job_id, status, message)
    
    async def execute_print(self, content, order_id):
        """执行打印"""
        method = self.config['print_methods'].get('method', 'file')
        
        self.logger.info(f"🖨️ 使用 {method} 方式打印...")
        
        if method == 'network':
            return await self.print_via_network(content)
        elif method == 'file':
            return await self.print_to_file(content, order_id)
        elif method == 'system':
            return await self.print_via_system(content)
        elif method == 'escpos':
            return await self.print_via_escpos(content)
        else:
            self.logger.error(f"❌ 未知的打印方式: {method}")
            return False
    
    async def print_via_network(self, content):
        """通过网络打印"""
        try:
            network_config = self.config['print_methods']['network']
            host = network_config['host']
            port = network_config['port']
            timeout = network_config.get('timeout', 10)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(content.encode('utf-8'))
            sock.close()
            
            self.logger.info(f"✅ 网络打印成功: {host}:{port}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 网络打印失败: {e}")
            return False
    
    async def print_to_file(self, content, order_id):
        """保存到文件"""
        try:
            file_config = self.config['print_methods'].get('file', {})
            directory = file_config.get('directory', './prints/')
            filename_format = file_config.get('filename_format', 'order_{order_id}_{timestamp}.txt')
            
            # 创建目录
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = filename_format.format(
                order_id=order_id,
                timestamp=timestamp
            )
            filepath = os.path.join(directory, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"✅ 文件保存成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件保存失败: {e}")
            return False
    
    async def print_via_system(self, content):
        """通过系统命令打印"""
        try:
            system_config = self.config['print_methods']['system']
            printer_name = system_config['printer_name']
            command_template = system_config['command']
            
            command = command_template.format(printer_name=printer_name)
            
            process = subprocess.Popen(
                command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=content.encode('utf-8'))
            
            if process.returncode == 0:
                self.logger.info("✅ 系统打印成功")
                return True
            else:
                self.logger.error(f"❌ 系统打印失败: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 系统打印异常: {e}")
            return False
    
    async def print_via_escpos(self, content):
        """通过ESC/POS打印"""
        try:
            # 需要安装: pip install python-escpos
            from escpos.printer import Network
            
            escpos_config = self.config['print_methods']['escpos']
            host = escpos_config['host']
            port = escpos_config['port']
            
            printer = Network(host, port)
            printer.text(content)
            printer.cut()
            printer.close()
            
            self.logger.info(f"✅ ESC/POS打印成功: {host}:{port}")
            return True
            
        except ImportError:
            self.logger.error("❌ 请安装 python-escpos: pip install python-escpos")
            return False
        except Exception as e:
            self.logger.error(f"❌ ESC/POS打印失败: {e}")
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
        self.logger.info(f"📤 状态反馈: {status} - {message}")
    
    async def send_pong(self, websocket):
        """发送心跳响应"""
        pong = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(pong))

def main():
    """主函数"""
    print("🖨️ 发财小狗饮品店 - 高级版打印客户端")
    print("=" * 60)
    
    # 检查配置文件
    config_file = 'print_client_config.json'
    if not os.path.exists(config_file):
        print(f"⚠️ 配置文件 {config_file} 不存在，将使用默认配置")
    
    print("💡 提示:")
    print("   1. 确保发财小狗饮品店应用正在运行")
    print("   2. 修改配置文件以适应您的环境")
    print("   3. 在管理后台确认订单时选择'启用自动打印'")
    print("   4. 按 Ctrl+C 退出程序")
    print("=" * 60)
    print()
    
    # 启动客户端
    client = AdvancedPrintClient(config_file)
    
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("\n⏹️ 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")

if __name__ == '__main__':
    main()
