#!/usr/bin/env python3
"""
升级所有路由到Element UI模板
"""

import re
import os

def upgrade_admin_routes():
    """升级管理员路由文件"""
    routes_file = 'app/admin/routes.py'
    
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 需要替换的模式
    patterns = [
        # 订单管理
        (r"return render_template\('admin/orders\.html'", "return render_template('admin/element_orders.html'"),
        # 客户管理
        (r"return render_template\('admin/customers\.html'", "return render_template('admin/element_customers.html'"),
        # 分类管理
        (r"return render_template\('admin/categories\.html'", "return render_template('admin/element_categories.html'"),
        # 产品管理
        (r"return render_template\('admin/products\.html'", "return render_template('admin/element_products.html'"),
        # 公告管理
        (r"return render_template\('admin/announcements\.html'", "return render_template('admin/element_announcements.html'"),
        # 打印管理
        (r"return render_template\('admin/print_management\.html'", "return render_template('admin/element_print_management.html'"),
    ]
    
    # 应用替换
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # 移除所有的 use_element 逻辑
    # 查找并替换包含 use_element 的代码块
    use_element_pattern = r'# 默认使用Element UI版本.*?else:\s*return render_template\([^)]+\)'
    
    def replace_use_element(match):
        text = match.group(0)
        # 提取Element UI的render_template调用
        element_pattern = r"return render_template\('admin/element_[^']+\.html'[^)]*\)"
        element_match = re.search(element_pattern, text)
        if element_match:
            return element_match.group(0)
        return text
    
    content = re.sub(use_element_pattern, replace_use_element, content, flags=re.DOTALL)
    
    # 写回文件
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 管理员路由已升级到Element UI")

def upgrade_main_routes():
    """升级主路由文件"""
    routes_file = 'app/main/routes.py'
    
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 需要替换的模式
    patterns = [
        # 首页
        (r"return render_template\('index\.html'", "return render_template('element_index.html'"),
        # 订单页面
        (r"return render_template\('order\.html'", "return render_template('element_order.html'"),
        # 订单详情
        (r"return render_template\('order_detail\.html'", "return render_template('element_order_detail.html'"),
        # 支付页面
        (r"return render_template\('payment\.html'", "return render_template('element_payment.html'"),
        # 取消订单
        (r"return render_template\('cancel_order\.html'", "return render_template('element_cancel_order.html'"),
        # 退款页面
        (r"return render_template\('refund_order_new\.html'", "return render_template('element_refund_order.html'"),
    ]
    
    # 应用替换
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 主路由已升级到Element UI")

def list_templates_to_delete():
    """列出需要删除的传统模板"""
    templates_dir = 'templates'
    admin_dir = 'templates/admin'
    
    # 需要删除的传统模板
    templates_to_delete = []
    
    # 管理员模板
    admin_templates = [
        'base.html', 'dashboard.html', 'orders.html', 'customers.html',
        'categories.html', 'products.html', 'announcements.html',
        'print_management.html', 'menu_config.html', 'payment_config.html',
        'pushdeer_configs.html', 'push_records.html', 'push_record_detail.html'
    ]
    
    for template in admin_templates:
        path = os.path.join(admin_dir, template)
        if os.path.exists(path):
            templates_to_delete.append(path)
    
    # 前台模板
    main_templates = [
        'base.html', 'index.html', 'order.html', 'order_detail.html',
        'payment.html', 'cancel_order.html', 'refund_order_new.html'
    ]
    
    for template in main_templates:
        path = os.path.join(templates_dir, template)
        if os.path.exists(path):
            templates_to_delete.append(path)
    
    return templates_to_delete

if __name__ == '__main__':
    print("🚀 开始升级到Element UI...")
    
    # 升级路由
    upgrade_admin_routes()
    upgrade_main_routes()
    
    # 列出需要删除的模板
    templates_to_delete = list_templates_to_delete()
    
    print(f"\n📋 需要删除的传统模板文件 ({len(templates_to_delete)} 个):")
    for template in templates_to_delete:
        print(f"  - {template}")
    
    print("\n⚠️  请确认所有Element UI模板都已创建并测试正常后，再删除传统模板文件。")
    print("🎉 升级完成！")
