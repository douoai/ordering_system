#!/usr/bin/env python3
"""
打印机接口服务
支持多种打印机类型和打印方式
"""
import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models import db, Order, OrderItem

class PrinterService:
    """打印机服务类"""
    
    def __init__(self):
        self.printer_configs = {
            'thermal': {
                'name': '热敏打印机',
                'width': 58,  # 58mm
                'encoding': 'gbk',
                'line_height': 24
            },
            'receipt': {
                'name': '收据打印机',
                'width': 80,  # 80mm
                'encoding': 'utf-8',
                'line_height': 20
            },
            'kitchen': {
                'name': '厨房打印机',
                'width': 58,  # 58mm
                'encoding': 'gbk',
                'line_height': 24
            }
        }
    
    def print_kitchen_ticket(self, order_id: int, printer_type: str = 'kitchen') -> Dict[str, Any]:
        """
        打印制作小票
        
        Args:
            order_id: 订单ID
            printer_type: 打印机类型
            
        Returns:
            Dict: 打印结果
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            # 生成制作小票内容
            ticket_content = self._generate_kitchen_ticket_content(order, printer_type)
            
            # 发送到打印机
            result = self._send_to_printer(ticket_content, printer_type, 'kitchen_ticket')
            
            # 记录打印日志
            self._log_print_record(order_id, 'kitchen_ticket', printer_type, result)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'打印制作小票失败: {str(e)}'}
    
    def print_receipt(self, order_id: int, printer_type: str = 'receipt') -> Dict[str, Any]:
        """
        打印收据
        
        Args:
            order_id: 订单ID
            printer_type: 打印机类型
            
        Returns:
            Dict: 打印结果
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            # 生成收据内容
            receipt_content = self._generate_receipt_content(order, printer_type)
            
            # 发送到打印机
            result = self._send_to_printer(receipt_content, printer_type, 'receipt')
            
            # 记录打印日志
            self._log_print_record(order_id, 'receipt', printer_type, result)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'打印收据失败: {str(e)}'}
    
    def print_order_detail(self, order_id: int, printer_type: str = 'receipt') -> Dict[str, Any]:
        """
        打印订单详情
        
        Args:
            order_id: 订单ID
            printer_type: 打印机类型
            
        Returns:
            Dict: 打印结果
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            # 生成订单详情内容
            order_content = self._generate_order_detail_content(order, printer_type)
            
            # 发送到打印机
            result = self._send_to_printer(order_content, printer_type, 'order_detail')
            
            # 记录打印日志
            self._log_print_record(order_id, 'order_detail', printer_type, result)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'打印订单详情失败: {str(e)}'}
    
    def _generate_kitchen_ticket_content(self, order: Order, printer_type: str) -> str:
        """生成制作小票内容"""
        config = self.printer_configs.get(printer_type, self.printer_configs['kitchen'])
        width = config['width']
        
        lines = []
        
        # 店铺信息
        lines.append(self._center_text("发财小狗饮品店", width))
        lines.append(self._center_text("制作小票", width))
        lines.append("=" * width)
        
        # 订单信息
        lines.append(f"订单号: #{order.id}")
        lines.append(f"客户: {order.user.username}")
        lines.append(f"时间: {order.created_at.strftime('%H:%M')}")
        lines.append(f"状态: {order.status_display}")
        lines.append("-" * width)
        
        # 制作项目
        for item in order.order_items:
            lines.append(f"【{item.drink_product.name}】")
            lines.append(f"数量: {item.quantity} 杯")
            
            # 制作规格
            if item.temperature:
                temp_text = self._get_temperature_text(item.temperature)
                lines.append(f"温度: {temp_text}")
            
            if item.sugar_level:
                sugar_text = self._get_sugar_level_text(item.sugar_level)
                lines.append(f"糖度: {sugar_text}")
            
            if item.ice_level:
                ice_text = self._get_ice_level_text(item.ice_level)
                lines.append(f"冰量: {ice_text}")
            
            if item.notes:
                lines.append(f"备注: {item.notes}")
            
            lines.append("-" * width)
        
        # 总计
        lines.append(f"总计: {order.total_items} 杯")
        lines.append("=" * width)
        lines.append(self._center_text("请按要求制作", width))
        lines.append(self._center_text(f"制作时间: {datetime.now().strftime('%H:%M')}", width))
        
        return "\n".join(lines)
    
    def _generate_receipt_content(self, order: Order, printer_type: str) -> str:
        """生成收据内容"""
        config = self.printer_configs.get(printer_type, self.printer_configs['receipt'])
        width = config['width']
        
        lines = []
        
        # 店铺信息
        lines.append(self._center_text("发财小狗饮品店", width))
        lines.append(self._center_text("购物收据", width))
        lines.append("=" * width)
        
        # 订单信息
        lines.append(f"收据号: #{order.id}")
        lines.append(f"客户: {order.user.username}")
        lines.append(f"电话: {order.user.phone or '未提供'}")
        lines.append(f"时间: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("-" * width)
        
        # 商品明细
        lines.append("商品明细:")
        for item in order.order_items:
            lines.append(f"{item.drink_product.name}")
            
            # 规格信息
            specs = []
            if item.temperature:
                specs.append(self._get_temperature_text(item.temperature))
            if item.sugar_level:
                specs.append(self._get_sugar_level_text(item.sugar_level))
            if item.ice_level:
                specs.append(self._get_ice_level_text(item.ice_level))
            
            if specs:
                lines.append(f"  规格: {' | '.join(specs)}")
            
            lines.append(f"  ¥{item.unit_price:.2f} x {item.quantity} = ¥{item.subtotal:.2f}")
            
            if item.notes:
                lines.append(f"  备注: {item.notes}")
        
        lines.append("-" * width)
        
        # 总计
        lines.append(f"商品数量: {order.total_items} 件")
        lines.append(f"应付金额: ¥{order.total_amount:.2f}")
        lines.append(f"实付金额: ¥{order.total_amount:.2f}")
        lines.append("=" * width)
        
        # 页脚
        lines.append(self._center_text("感谢您的光临!", width))
        lines.append(self._center_text("欢迎再次选择发财小狗饮品店", width))
        lines.append(self._center_text(f"打印时间: {datetime.now().strftime('%m-%d %H:%M')}", width))
        
        return "\n".join(lines)
    
    def _generate_order_detail_content(self, order: Order, printer_type: str) -> str:
        """生成订单详情内容"""
        config = self.printer_configs.get(printer_type, self.printer_configs['receipt'])
        width = config['width']
        
        lines = []
        
        # 店铺信息
        lines.append(self._center_text("发财小狗饮品店", width))
        lines.append(self._center_text("订单详情", width))
        lines.append("=" * width)
        
        # 详细订单信息
        lines.append(f"订单号: #{order.id}")
        lines.append(f"客户姓名: {order.user.username}")
        lines.append(f"联系电话: {order.user.phone or '未提供'}")
        lines.append(f"邮箱地址: {order.user.email or '未提供'}")
        lines.append(f"下单时间: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"订单状态: {order.status_display}")
        
        if order.user.address:
            lines.append(f"送货地址: {order.user.address}")
        
        if order.notes:
            lines.append(f"订单备注: {order.notes}")
        
        lines.append("-" * width)
        
        # 商品明细
        lines.append("订单明细:")
        for item in order.order_items:
            lines.append(f"商品: {item.drink_product.name}")
            lines.append(f"单价: ¥{item.unit_price:.2f}")
            lines.append(f"数量: {item.quantity}")
            lines.append(f"小计: ¥{item.subtotal:.2f}")
            
            # 制作规格
            if item.temperature:
                lines.append(f"温度: {self._get_temperature_text(item.temperature)}")
            if item.sugar_level:
                lines.append(f"糖度: {self._get_sugar_level_text(item.sugar_level)}")
            if item.ice_level:
                lines.append(f"冰量: {self._get_ice_level_text(item.ice_level)}")
            if item.notes:
                lines.append(f"备注: {item.notes}")
            
            lines.append("")
        
        lines.append("-" * width)
        lines.append(f"商品总数: {order.total_items} 件")
        lines.append(f"订单总额: ¥{order.total_amount:.2f}")
        lines.append("=" * width)
        lines.append(self._center_text(f"打印时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", width))
        
        return "\n".join(lines)
    
    def _send_to_printer(self, content: str, printer_type: str, print_type: str) -> Dict[str, Any]:
        """
        发送内容到打印机
        这里可以对接不同的打印机接口
        """
        try:
            # 这里是打印机接口对接的地方
            # 可以根据实际使用的打印机类型进行对接
            
            # 示例：对接网络打印机
            # result = self._send_to_network_printer(content, printer_type)
            
            # 示例：对接USB打印机
            # result = self._send_to_usb_printer(content, printer_type)
            
            # 示例：对接云打印服务
            # result = self._send_to_cloud_printer(content, printer_type)
            
            # 目前返回模拟成功结果
            return {
                'success': True,
                'message': f'打印任务已发送到{self.printer_configs[printer_type]["name"]}',
                'printer_type': printer_type,
                'print_type': print_type,
                'content_length': len(content)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'发送到打印机失败: {str(e)}'
            }
    
    def _send_to_network_printer(self, content: str, printer_ip: str, printer_port: int = 9100) -> Dict[str, Any]:
        """发送到网络打印机"""
        try:
            import socket
            
            # 创建socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((printer_ip, printer_port))
            
            # 发送打印内容
            sock.send(content.encode('gbk'))
            sock.close()
            
            return {'success': True, 'message': '网络打印成功'}
            
        except Exception as e:
            return {'success': False, 'error': f'网络打印失败: {str(e)}'}
    
    def _send_to_cloud_printer(self, content: str, api_url: str, api_key: str) -> Dict[str, Any]:
        """发送到云打印服务"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            data = {
                'content': content,
                'printer_type': 'thermal',
                'copies': 1
            }
            
            response = requests.post(api_url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return {'success': True, 'message': '云打印成功', 'response': response.json()}
            else:
                return {'success': False, 'error': f'云打印失败: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'云打印失败: {str(e)}'}
    
    def _center_text(self, text: str, width: int) -> str:
        """居中文本"""
        text_len = len(text.encode('gbk'))
        if text_len >= width:
            return text
        padding = (width - text_len) // 2
        return ' ' * padding + text
    
    def _get_temperature_text(self, temperature: str) -> str:
        """获取温度显示文本"""
        temp_map = {
            'hot': '热饮',
            'ice': '冰饮',
            'room': '常温'
        }
        return temp_map.get(temperature, temperature)
    
    def _get_sugar_level_text(self, sugar_level: str) -> str:
        """获取糖度显示文本"""
        sugar_map = {
            'no_sugar': '无糖',
            'less_sugar': '少糖',
            'half_sugar': '半糖',
            'normal_sugar': '正常糖',
            'extra_sugar': '多糖'
        }
        return sugar_map.get(sugar_level, sugar_level)
    
    def _get_ice_level_text(self, ice_level: str) -> str:
        """获取冰量显示文本"""
        ice_map = {
            'no_ice': '去冰',
            'less_ice': '少冰',
            'normal_ice': '正常冰',
            'extra_ice': '多冰'
        }
        return ice_map.get(ice_level, ice_level)
    
    def _log_print_record(self, order_id: int, print_type: str, printer_type: str, result: Dict[str, Any]):
        """记录打印日志"""
        try:
            # 这里可以创建打印记录表来记录所有打印操作
            # 暂时使用简单的日志记录
            print(f"打印日志 - 订单:{order_id}, 类型:{print_type}, 打印机:{printer_type}, 结果:{result['success']}")
        except Exception as e:
            print(f"记录打印日志失败: {e}")

# 创建全局打印服务实例
printer_service = PrinterService()
