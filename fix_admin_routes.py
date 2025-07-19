#!/usr/bin/env python3
"""
修复管理员路由，统一使用Element UI模板
"""

import re

def fix_admin_routes():
    """修复管理员路由文件"""
    routes_file = 'app/admin/routes.py'
    
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 直接替换所有传统模板为Element UI模板
    template_replacements = [
        ("render_template('admin/orders.html'", "render_template('admin/element_orders.html'"),
        ("render_template('admin/customers.html'", "render_template('admin/element_customers.html'"),
        ("render_template('admin/categories.html'", "render_template('admin/element_categories.html'"),
        ("render_template('admin/products.html'", "render_template('admin/element_products.html'"),
        ("render_template('admin/announcements.html'", "render_template('admin/element_announcements.html'"),
        ("render_template('admin/print_management.html'", "render_template('admin/element_print_management.html'"),
        ("render_template('admin/menu_config.html'", "render_template('admin/element_menu_config.html'"),
        ("render_template('admin/payment_config.html'", "render_template('admin/element_payment_config.html'"),
        ("render_template('admin/pushdeer_configs.html'", "render_template('admin/element_pushdeer_configs.html'"),
        ("render_template('admin/push_records.html'", "render_template('admin/element_push_records.html'"),
        ("render_template('admin/push_record_detail.html'", "render_template('admin/element_push_record_detail.html'"),
    ]
    
    for old_template, new_template in template_replacements:
        content = content.replace(old_template, new_template)
    
    # 移除所有 use_element 相关的逻辑
    # 查找并替换包含 use_element 的代码块
    use_element_patterns = [
        # 模式1: 标准的 use_element 检查
        r'# 默认使用Element UI版本.*?use_element = request\.args\.get\([^)]+\)[^}]*?if use_element:\s*return render_template\([^)]+\)\s*else:\s*return render_template\([^)]+\)',
        # 模式2: 简化的 use_element 检查
        r'use_element = request\.args\.get\([^)]+\)[^}]*?if use_element:\s*return render_template\([^)]+\)\s*else:\s*return render_template\([^)]+\)',
    ]
    
    for pattern in use_element_patterns:
        matches = re.finditer(pattern, content, re.DOTALL)
        for match in matches:
            text = match.group(0)
            # 提取Element UI的render_template调用
            element_pattern = r"return render_template\('admin/element_[^']+\.html'[^)]*\)"
            element_match = re.search(element_pattern, text)
            if element_match:
                content = content.replace(text, element_match.group(0))
    
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 管理员路由已升级完成")

def fix_main_routes():
    """修复主路由文件"""
    routes_file = 'app/main/routes.py'
    
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 直接替换所有传统模板为Element UI模板
    template_replacements = [
        ("render_template('index.html'", "render_template('element_index.html'"),
        ("render_template('order.html'", "render_template('element_order.html'"),
        ("render_template('order_detail.html'", "render_template('element_order_detail.html'"),
        ("render_template('payment.html'", "render_template('element_payment.html'"),
        ("render_template('cancel_order.html'", "render_template('element_cancel_order.html'"),
        ("render_template('refund_order_new.html'", "render_template('element_refund_order.html'"),
        ("render_template('my_orders.html'", "render_template('element_my_orders.html'"),
        ("render_template('order_success.html'", "render_template('element_order_success.html'"),
        ("render_template('user_info.html'", "render_template('element_user_info.html'"),
    ]
    
    for old_template, new_template in template_replacements:
        content = content.replace(old_template, new_template)
    
    # 移除 use_element 相关逻辑
    use_element_patterns = [
        r'# 检查是否使用Element UI版本.*?use_element = request\.args\.get\([^)]+\)[^}]*?if use_element:\s*return render_template\([^)]+\)\s*else:\s*return render_template\([^)]+\)',
        r'use_element = request\.args\.get\([^)]+\)[^}]*?if use_element:\s*return render_template\([^)]+\)\s*else:\s*return render_template\([^)]+\)',
    ]
    
    for pattern in use_element_patterns:
        matches = re.finditer(pattern, content, re.DOTALL)
        for match in matches:
            text = match.group(0)
            # 提取Element UI的render_template调用
            element_pattern = r"return render_template\('element_[^']+\.html'[^)]*\)"
            element_match = re.search(element_pattern, text)
            if element_match:
                content = content.replace(text, element_match.group(0))
    
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 主路由已升级完成")

if __name__ == '__main__':
    print("🚀 开始修复路由...")
    fix_admin_routes()
    fix_main_routes()
    print("🎉 路由修复完成！")
