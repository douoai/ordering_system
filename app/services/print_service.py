#!/usr/bin/env python3
"""
打印服务
处理订单打印逻辑
"""

import asyncio
import json
from datetime import datetime
from app.models import db, PrintJob, PrinterConfig, Order
from app.websocket.print_server import print_server

class PrintService:
    """打印服务类"""
    
    @staticmethod
    def create_order_print_job(order, printer=None, copies=1):
        """创建订单打印任务"""
        try:
            # 如果没有指定打印机，使用默认的自动打印打印机
            if not printer:
                printer = PrinterConfig.query.filter_by(
                    is_active=True, 
                    auto_print_orders=True
                ).first()
            
            # 生成打印内容
            print_content = PrintService.generate_order_receipt(order)
            
            # 创建打印任务
            job = PrintJob(
                order_id=order.id,
                printer_id=printer.id if printer else None,
                job_type='order',
                status='pending',
                print_content=print_content,
                copies=copies,
                priority=1 if order.status == 'confirmed' else 5
            )
            
            db.session.add(job)
            db.session.commit()
            
            return job
            
        except Exception as e:
            print(f"创建打印任务失败: {e}")
            return None
    
    @staticmethod
    def generate_order_receipt(order):
        """生成订单小票内容"""
        try:
            # 小票头部
            receipt = "================================\n"
            receipt += "        发财小狗饮品店\n"
            receipt += "================================\n"
            receipt += f"订单号: #{order.id}\n"
            receipt += f"时间: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            receipt += f"状态: {order.status_display}\n"
            receipt += "--------------------------------\n"
            
            # 商品列表
            total_amount = 0
            for item in order.order_items:
                receipt += f"{item.drink_product.name}\n"
                
                # 规格信息
                specs = []
                if item.size:
                    specs.append(f"规格: {item.size}")
                if item.temperature:
                    specs.append(f"温度: {item.temperature}")
                if item.sugar_level:
                    specs.append(f"糖度: {item.sugar_level}")
                if item.ice_level:
                    specs.append(f"冰量: {item.ice_level}")
                
                if specs:
                    receipt += f"  {' | '.join(specs)}\n"
                
                if item.notes:
                    receipt += f"  备注: {item.notes}\n"
                
                receipt += f"  {item.quantity} x ¥{item.unit_price:.2f} = ¥{item.subtotal:.2f}\n"
                receipt += "--------------------------------\n"
                total_amount += item.subtotal
            
            # 总计
            receipt += f"总计: ¥{total_amount:.2f}\n"
            
            # 订单备注
            if order.notes:
                receipt += "--------------------------------\n"
                receipt += f"订单备注: {order.notes}\n"
            
            # 小票尾部
            receipt += "================================\n"
            receipt += "      谢谢惠顾，欢迎再来！\n"
            receipt += "================================\n"
            
            return receipt
            
        except Exception as e:
            print(f"生成小票内容失败: {e}")
            return f"订单 #{order.id} 打印内容生成失败"
    
    @staticmethod
    async def send_order_to_printer(order):
        """发送订单到打印机"""
        try:
            # 创建打印任务
            job = PrintService.create_order_print_job(order)
            if not job:
                return False, "创建打印任务失败"
            
            # 构建打印数据
            print_data = {
                "job_id": job.id,
                "order_id": order.id,
                "type": "order_receipt",
                "content": job.print_content,
                "copies": job.copies,
                "priority": job.priority,
                "timestamp": datetime.now().isoformat(),
                "order_info": {
                    "id": order.id,
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "created_at": order.created_at.isoformat(),
                    "customer_phone": order.user.phone if order.user else None
                },
                "printer_config": {
                    "paper_width": job.printer.paper_width if job.printer else 80,
                    "printer_type": job.printer.printer_type if job.printer else "thermal"
                }
            }
            
            # 标记为正在打印
            job.mark_as_printing()
            db.session.commit()
            
            # 发送到WebSocket服务器
            success = await print_server.broadcast_order(print_data)
            
            if success:
                job.mark_as_completed()
                db.session.commit()
                return True, "订单已发送到打印机"
            else:
                job.mark_as_failed("没有可用的打印客户端")
                db.session.commit()
                return False, "没有连接的打印客户端"
                
        except Exception as e:
            if 'job' in locals():
                job.mark_as_failed(str(e))
                db.session.commit()
            return False, f"发送失败: {str(e)}"
    
    @staticmethod
    def send_order_to_printer_sync(order):
        """同步方式发送订单到打印机"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步函数
            success, message = loop.run_until_complete(
                PrintService.send_order_to_printer(order)
            )

            loop.close()
            return success, message

        except Exception as e:
            return False, f"同步发送失败: {str(e)}"

    @staticmethod
    async def send_order_to_specific_printer(order, printer=None):
        """发送订单到指定打印机"""
        try:
            # 创建打印任务，使用指定的打印机
            job = PrintService.create_order_print_job(order, printer)
            if not job:
                return False, "创建打印任务失败"

            # 构建打印数据
            print_data = {
                "job_id": job.id,
                "order_id": order.id,
                "type": "order_receipt",
                "content": job.print_content,
                "copies": job.copies,
                "priority": job.priority,
                "timestamp": datetime.now().isoformat(),
                "target_printer": {
                    "id": printer.id if printer else None,
                    "name": printer.name if printer else "默认打印机",
                    "ip_address": printer.ip_address if printer else None
                },
                "order_info": {
                    "id": order.id,
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "created_at": order.created_at.isoformat(),
                    "customer_phone": order.user.phone if order.user else None
                },
                "printer_config": {
                    "paper_width": job.printer.paper_width if job.printer else 80,
                    "printer_type": job.printer.printer_type if job.printer else "thermal"
                }
            }

            # 标记为正在打印
            job.mark_as_printing()
            db.session.commit()

            # 发送到WebSocket服务器
            success = await print_server.broadcast_order(print_data)

            if success:
                job.mark_as_completed()
                db.session.commit()
                printer_name = printer.name if printer else "默认打印机"
                return True, f"订单已发送到 {printer_name}"
            else:
                job.mark_as_failed("没有可用的打印客户端")
                db.session.commit()
                return False, "没有连接的打印客户端"

        except Exception as e:
            if 'job' in locals():
                job.mark_as_failed(str(e))
                db.session.commit()
            return False, f"发送失败: {str(e)}"

    @staticmethod
    def send_order_to_specific_printer_sync(order, printer=None):
        """同步方式发送订单到指定打印机"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步函数
            success, message = loop.run_until_complete(
                PrintService.send_order_to_specific_printer(order, printer)
            )

            loop.close()
            return success, message

        except Exception as e:
            return False, f"同步发送失败: {str(e)}"
    
    @staticmethod
    def get_pending_jobs():
        """获取待处理的打印任务"""
        return PrintJob.query.filter_by(status='pending').order_by(
            PrintJob.priority.asc(),
            PrintJob.created_at.asc()
        ).all()
    
    @staticmethod
    def retry_failed_jobs():
        """重试失败的打印任务"""
        failed_jobs = PrintJob.query.filter(
            PrintJob.status == 'failed',
            PrintJob.retry_count < PrintJob.max_retries
        ).all()
        
        retry_count = 0
        for job in failed_jobs:
            try:
                # 重置状态
                job.status = 'pending'
                job.error_message = None
                db.session.commit()
                
                # 重新发送
                success, message = PrintService.send_order_to_printer_sync(job.order)
                if success:
                    retry_count += 1
                    
            except Exception as e:
                print(f"重试任务 {job.id} 失败: {e}")
        
        return retry_count
    
    @staticmethod
    def get_print_statistics():
        """获取打印统计信息"""
        from sqlalchemy import func
        
        stats = {
            'total_jobs': PrintJob.query.count(),
            'pending_jobs': PrintJob.query.filter_by(status='pending').count(),
            'printing_jobs': PrintJob.query.filter_by(status='printing').count(),
            'completed_jobs': PrintJob.query.filter_by(status='completed').count(),
            'failed_jobs': PrintJob.query.filter_by(status='failed').count(),
            'cancelled_jobs': PrintJob.query.filter_by(status='cancelled').count(),
        }
        
        # 今日统计
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats['today_completed'] = PrintJob.query.filter(
            PrintJob.status == 'completed',
            PrintJob.completed_at >= today
        ).count()
        
        stats['today_failed'] = PrintJob.query.filter(
            PrintJob.status == 'failed',
            PrintJob.created_at >= today
        ).count()
        
        return stats

# 便捷函数
def print_order(order):
    """打印订单（同步方式）"""
    return PrintService.send_order_to_printer_sync(order)

def print_order_to_specific_printer(order, printer=None):
    """打印订单到指定打印机（同步方式）"""
    return PrintService.send_order_to_specific_printer_sync(order, printer)

async def print_order_async(order):
    """打印订单（异步方式）"""
    return await PrintService.send_order_to_printer(order)

async def print_order_to_specific_printer_async(order, printer=None):
    """打印订单到指定打印机（异步方式）"""
    return await PrintService.send_order_to_specific_printer(order, printer)
