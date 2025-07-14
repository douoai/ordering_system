#!/usr/bin/env python3
"""
WebSocket打印服务器
系统作为服务端，推送订单信息给外部打印设备
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any
import threading
import queue

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrintServer:
    """WebSocket打印服务器"""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.print_queue = queue.Queue()
        self.server = None
        self.is_running = False
        
    async def register_client(self, websocket, path):
        """注册新的打印客户端"""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"新客户端尝试连接: {client_info}")

        try:
            # 添加到客户端列表
            self.clients.add(websocket)
            logger.info(f"打印客户端已连接: {client_info}, 当前连接数: {len(self.clients)}")

            # 发送欢迎消息
            welcome_msg = {
                "type": "welcome",
                "message": "欢迎连接到发财小狗饮品店打印服务",
                "timestamp": datetime.now().isoformat(),
                "server_info": {
                    "name": "发财小狗饮品店打印服务器",
                    "version": "1.0.0",
                    "capabilities": ["order_print", "receipt_print", "status_update"]
                }
            }
            await websocket.send(json.dumps(welcome_msg, ensure_ascii=False))
            logger.info(f"已发送欢迎消息给客户端: {client_info}")

            # 保持连接并处理客户端消息
            async for message in websocket:
                try:
                    await self.handle_client_message(websocket, message)
                except Exception as e:
                    logger.error(f"处理客户端 {client_info} 消息时出错: {e}")
                    # 不要因为单个消息处理错误而断开连接
                    continue

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"打印客户端正常断开: {client_info}, 原因: {e}")
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket异常 {client_info}: {e}")
        except Exception as e:
            logger.error(f"客户端 {client_info} 连接异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 确保从客户端列表中移除
            self.clients.discard(websocket)
            logger.info(f"客户端已移除: {client_info}, 剩余连接数: {len(self.clients)}")
    
    async def handle_client_message(self, websocket, message):
        """处理客户端消息"""
        try:
            logger.info(f"收到原始消息: {message[:100]}...")  # 只显示前100个字符
            data = json.loads(message)
            msg_type = data.get('type')

            logger.info(f"处理消息类型: {msg_type}")

            if msg_type == 'ping':
                # 心跳响应
                pong_msg = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(pong_msg))
                logger.info("已发送pong响应")

            elif msg_type == 'print_status':
                # 打印状态更新
                logger.info(f"收到打印状态: {data}")
                # 这里可以更新数据库中的打印状态

            elif msg_type == 'printer_info':
                # 打印机信息
                logger.info(f"收到打印机信息: {data.get('printer', {}).get('name', 'Unknown')}")

                # 发送确认响应
                ack_msg = {
                    "type": "printer_info_ack",
                    "timestamp": datetime.now().isoformat(),
                    "message": "打印机信息已收到"
                }
                await websocket.send(json.dumps(ack_msg, ensure_ascii=False))
                logger.info("已发送打印机信息确认")

            else:
                logger.warning(f"未知消息类型: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}, 消息: {message}")
        except Exception as e:
            logger.error(f"处理客户端消息时出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def broadcast_order(self, order_data):
        """广播订单信息给所有连接的打印客户端"""
        if not self.clients:
            logger.warning("没有连接的打印客户端")
            return False
        
        message = {
            "type": "new_order",
            "timestamp": datetime.now().isoformat(),
            "order": order_data
        }
        
        # 发送给所有连接的客户端
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
                logger.info(f"订单已发送给客户端: {client.remote_address}")
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"发送订单失败: {e}")
                disconnected_clients.add(client)
        
        # 清理断开的连接
        self.clients -= disconnected_clients
        
        return len(self.clients) > 0
    
    async def send_print_command(self, print_data):
        """发送打印命令"""
        if not self.clients:
            logger.warning("没有连接的打印客户端")
            return False
        
        message = {
            "type": "print_command",
            "timestamp": datetime.now().isoformat(),
            "data": print_data
        }
        
        # 发送给所有连接的客户端
        success_count = 0
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
                success_count += 1
                logger.info(f"打印命令已发送给客户端: {client.remote_address}")
            except websockets.exceptions.ConnectionClosed:
                self.clients.discard(client)
            except Exception as e:
                logger.error(f"发送打印命令失败: {e}")
                self.clients.discard(client)
        
        return success_count > 0
    
    async def get_client_status(self):
        """获取客户端状态"""
        status_requests = []
        for client in self.clients.copy():
            try:
                status_request = {
                    "type": "status_request",
                    "timestamp": datetime.now().isoformat()
                }
                await client.send(json.dumps(status_request))
                status_requests.append(client.remote_address)
            except websockets.exceptions.ConnectionClosed:
                self.clients.discard(client)
            except Exception as e:
                logger.error(f"请求状态失败: {e}")
                self.clients.discard(client)
        
        return status_requests
    
    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            logger.info(f"正在启动WebSocket服务器 {self.host}:{self.port}...")

            # 创建处理函数包装器
            async def handler(websocket, path):
                await self.register_client(websocket, path)

            self.server = await websockets.serve(
                handler,
                self.host,
                self.port,
                ping_interval=30,  # 30秒心跳
                ping_timeout=10,   # 10秒超时
                max_size=1024*1024,  # 1MB最大消息大小
                max_queue=32,        # 最大队列大小
                compression=None     # 禁用压缩以提高性能
            )
            self.is_running = True
            logger.info(f"✅ 打印服务器已启动: ws://{self.host}:{self.port}")
            logger.info(f"服务器配置: ping_interval=30s, ping_timeout=10s")

            # 保持服务器运行
            await self.server.wait_closed()

        except OSError as e:
            if e.errno == 10048:  # Windows端口被占用
                logger.error(f"端口 {self.port} 已被占用，请检查是否有其他程序在使用")
            else:
                logger.error(f"网络错误: {e}")
            self.is_running = False
        except Exception as e:
            logger.error(f"启动打印服务器失败: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    async def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("打印服务器已停止")
    
    def get_status(self):
        """获取服务器状态"""
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "connected_clients": len(self.clients),
            "client_addresses": [f"{client.remote_address[0]}:{client.remote_address[1]}" 
                               for client in self.clients]
        }

# 全局打印服务器实例
print_server = PrintServer()

def start_print_server_thread():
    """在新线程中启动打印服务器"""
    def run_server():
        try:
            logger.info("🚀 WebSocket服务器线程启动")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 添加异常处理
            try:
                loop.run_until_complete(print_server.start_server())
            except KeyboardInterrupt:
                logger.info("WebSocket服务器被用户中断")
            except Exception as e:
                logger.error(f"WebSocket服务器运行异常: {e}")
                import traceback
                traceback.print_exc()
            finally:
                loop.close()
                logger.info("WebSocket服务器线程结束")

        except Exception as e:
            logger.error(f"WebSocket服务器线程启动失败: {e}")
            import traceback
            traceback.print_exc()

    thread = threading.Thread(target=run_server, daemon=True, name="WebSocketServer")
    thread.start()
    logger.info(f"WebSocket服务器线程已启动: {thread.name}")

    # 等待一小段时间让服务器启动
    import time
    time.sleep(1)

    return thread

async def send_order_to_printer(order_data):
    """发送订单到打印机"""
    return await print_server.broadcast_order(order_data)

async def send_print_command(print_data):
    """发送打印命令"""
    return await print_server.send_print_command(print_data)

def get_print_server_status():
    """获取打印服务器状态"""
    return print_server.get_status()
