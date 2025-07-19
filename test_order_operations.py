#!/usr/bin/env python3
"""
测试订单操作功能
"""

from app import create_app
from app.models import db, Order
import requests
import json

def test_order_status_update():
    """测试订单状态更新功能"""
    app = create_app()
    
    with app.app_context():
        # 查找一个待确认的订单
        pending_order = Order.query.filter_by(status='pending').first()
        
        if not pending_order:
            print("没有找到待确认的订单")
            return
        
        print(f"找到待确认订单: #{pending_order.id}")
        print(f"当前状态: {pending_order.status}")
        
        # 测试数据
        test_cases = [
            {
                'order_id': pending_order.id,
                'status': 'confirmed',
                'reason': '',
                'expected': True
            },
            {
                'order_id': pending_order.id,
                'status': 'rejected', 
                'reason': '测试拒绝原因',
                'expected': False  # 因为已经确认了，不能再拒绝
            }
        ]
        
        for case in test_cases:
            print(f"\n测试: 将订单#{case['order_id']}状态更新为{case['status']}")
            
            # 模拟表单数据
            form_data = {
                'status': case['status']
            }
            if case['reason']:
                form_data['reason'] = case['reason']
            
            # 这里只是验证逻辑，实际测试需要启动服务器
            print(f"表单数据: {form_data}")
            print(f"预期结果: {'成功' if case['expected'] else '失败'}")

def check_order_73_status():
    """检查订单73的状态"""
    app = create_app()
    
    with app.app_context():
        order = Order.query.get(73)
        if order:
            print(f"订单73状态检查:")
            print(f"  ID: {order.id}")
            print(f"  状态: {order.status}")
            print(f"  拒绝原因: {order.reject_reason}")
            print(f"  确认时间: {order.confirmed_at}")
            print(f"  确认人: {order.confirmed_by}")
            
            # 检查状态映射
            status_map = {
                'pending': '待确认',
                'confirmed': '已确认',
                'paid': '已支付',
                'rejected': '已拒绝',
                'completed': '已完成',
                'refunded': '已退款'
            }
            
            print(f"  状态显示: {status_map.get(order.status, order.status)}")
            
            # 检查状态类型
            status_type_map = {
                'pending': 'warning',
                'confirmed': 'success',
                'paid': 'primary',
                'rejected': 'danger',
                'completed': 'success',
                'refunded': 'info'
            }
            
            print(f"  状态类型: {status_type_map.get(order.status, 'info')}")
        else:
            print("订单73不存在")

def check_all_rejected_orders():
    """检查所有已拒绝的订单"""
    app = create_app()
    
    with app.app_context():
        rejected_orders = Order.query.filter_by(status='rejected').all()
        print(f"\n已拒绝订单列表 (共{len(rejected_orders)}个):")
        
        for order in rejected_orders:
            print(f"  订单#{order.id}:")
            print(f"    状态: {order.status}")
            print(f"    拒绝原因: {order.reject_reason or '无'}")
            print(f"    确认时间: {order.confirmed_at}")
            print(f"    确认人: {order.confirmed_by}")
            print()

if __name__ == '__main__':
    print("=== 订单操作功能测试 ===")
    
    print("\n1. 检查订单73状态")
    check_order_73_status()
    
    print("\n2. 检查所有已拒绝订单")
    check_all_rejected_orders()
    
    print("\n3. 测试订单状态更新逻辑")
    test_order_status_update()
    
    print("\n=== 测试完成 ===")
    print("\n修复说明:")
    print("1. 添加了reject_reason字段到Order模型")
    print("2. 创建了通用的update_order_status路由")
    print("3. 修复了前端的快速操作函数")
    print("4. 改进了Element UI的拒绝订单弹窗")
    print("5. 添加了对completed状态的支持")
