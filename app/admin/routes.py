from flask import render_template, request, redirect, url_for, flash, session, make_response
from datetime import datetime
from functools import wraps
from app.admin import bp
from app.models import db, Order, User, DrinkProduct, OrderItem, Category, PushDeerConfig, PushRecord, Announcement, MenuConfig, AdminUser, AdminRole, Permission, PaymentConfig
from app.utils import save_uploaded_file, delete_uploaded_file
from app.services.pushdeer import pushdeer_service
from app.services.printer import printer_service
import json

def admin_required(f):
    """管理员登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('请先登录管理员账户', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@admin_required
def dashboard():
    """管理员仪表板"""
    # 统计数据
    pending_orders = Order.query.filter_by(status='pending').count()
    confirmed_orders = Order.query.filter_by(status='confirmed').count()
    completed_orders = Order.query.filter_by(status='completed').count()
    rejected_orders = Order.query.filter_by(status='rejected').count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_customers = User.query.count()

    # 今日数据
    today = datetime.now().date()
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).count()
    today_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
        db.func.date(Order.created_at) == today
    ).scalar() or 0
    today_customers = User.query.filter(db.func.date(User.created_at) == today).count()

    # 平均订单金额
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0

    # 热销产品（模拟数据）
    popular_products = [
        {'name': '美式咖啡', 'sales_count': 156, 'revenue': 1560.00},
        {'name': '拿铁咖啡', 'sales_count': 134, 'revenue': 1876.00},
        {'name': '卡布奇诺', 'sales_count': 98, 'revenue': 1372.00},
        {'name': '摩卡咖啡', 'sales_count': 87, 'revenue': 1305.00},
        {'name': '焦糖玛奇朵', 'sales_count': 76, 'revenue': 1292.00}
    ]

    # 最近订单
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # 检查是否使用Element UI版本
    use_element = request.args.get('ui') == 'element'

    template_data = {
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'completed_orders': completed_orders,
        'rejected_orders': rejected_orders,
        'total_orders': total_orders,
        'total_revenue': f"{total_revenue:.2f}",
        'total_customers': total_customers,
        'today_orders': today_orders,
        'today_revenue': f"{today_revenue:.2f}",
        'today_customers': today_customers,
        'avg_order_value': f"¥{avg_order_value:.2f}",
        'today_date': today.strftime('%Y年%m月%d日'),
        'popular_products': popular_products,
        'recent_orders': recent_orders
    }

    if use_element:
        return render_template('admin/element_dashboard.html', **template_data)
    else:
        return render_template('admin/dashboard.html', **template_data)

@bp.route('/orders')
@admin_required
def orders():
    """订单管理页面"""
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)

    # 强制刷新数据库连接，避免缓存问题
    db.session.expire_all()

    query = Order.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False  # 增加每页显示数量
    )

    # 检查是否使用Element UI版本
    use_element = request.args.get('ui') == 'element'

    if use_element:
        return render_template('admin/element_orders.html', orders=orders, status_filter=status_filter)
    else:
        return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@bp.route('/order/<int:order_id>')
@admin_required
def order_detail(order_id):
    """订单详情页面"""
    order = Order.query.get_or_404(order_id)

    # 获取可用的打印机列表
    try:
        from app.models import PrinterConfig
        available_printers = PrinterConfig.query.filter_by(is_active=True).all()
    except Exception as e:
        print(f"获取打印机列表失败: {e}")
        available_printers = []

    return render_template('admin/order_detail.html',
                         order=order,
                         available_printers=available_printers)

@bp.route('/order/<int:order_id>/confirm', methods=['POST'])
@admin_required
def confirm_order(order_id):
    """确认订单"""
    order = Order.query.get_or_404(order_id)

    if order.status not in ['pending', 'confirmed']:
        flash('订单状态不允许确认', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))
    
    order.status = 'confirmed'
    order.confirmed_at = datetime.utcnow()
    order.confirmed_by = session.get('admin_username', 'admin')  # 简化处理，实际应该有管理员登录

    # 更新用户统计信息
    order.user.update_order_stats()

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'order_confirmed')
    except Exception as e:
        print(f"推送通知失败: {e}")

    # 根据管理员选择决定是否自动打印
    auto_print = request.form.get('auto_print') == 'on'
    selected_printer_id = request.form.get('printer_id')

    if auto_print:
        try:
            from app.services.print_service import print_order_to_specific_printer
            from app.models import PrinterConfig

            # 获取指定的打印机
            printer = None
            if selected_printer_id:
                printer = PrinterConfig.query.get(selected_printer_id)

            success, message = print_order_to_specific_printer(order, printer)
            if success:
                printer_name = printer.name if printer else "默认打印机"
                flash(f'订单 {order_id} 已确认并发送到 {printer_name}', 'success')
            else:
                flash(f'订单 {order_id} 已确认，但打印失败: {message}', 'warning')
        except Exception as e:
            print(f"自动打印失败: {e}")
            flash(f'订单 {order_id} 已确认，但打印功能异常', 'warning')
    else:
        flash(f'订单 {order_id} 已确认', 'success')
    
    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/reject', methods=['POST'])
@admin_required
def reject_order(order_id):
    """拒绝订单"""
    order = Order.query.get_or_404(order_id)
    
    if order.status != 'pending':
        flash('订单状态不允许拒绝', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))
    
    order.status = 'rejected'
    order.confirmed_at = datetime.utcnow()
    order.confirmed_by = session.get('admin_username', 'admin')

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'order_cancelled')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 已拒绝', 'warning')
    
    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/approve_cancel', methods=['POST'])
@admin_required
def approve_cancel(order_id):
    """批准取消订单"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'cancel_pending':
        flash('订单状态不允许批准取消', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    order.status = 'cancelled'
    order.cancel_approved_by = session.get('admin_username', 'admin')
    order.cancel_approved_at = datetime.utcnow()

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'cancel_approved')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 取消申请已批准', 'success')

    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/reject_cancel', methods=['POST'])
@admin_required
def reject_cancel(order_id):
    """拒绝取消订单"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'cancel_pending':
        flash('订单状态不允许拒绝取消', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    # 恢复到之前的状态（通常是confirmed或paid）
    # 这里需要记录之前的状态，暂时设为confirmed
    order.status = 'confirmed'
    order.cancel_reason = None
    order.cancelled_by = None

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'cancel_rejected')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 取消申请已拒绝', 'warning')

    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/approve_refund', methods=['POST'])
@admin_required
def approve_refund(order_id):
    """批准退款申请"""
    order = Order.query.get_or_404(order_id)

    if order.refund_status != 'pending':
        flash('退款状态不允许批准', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    admin_notes = request.form.get('admin_notes', '').strip()

    order.refund_status = 'approved'
    order.refund_approved_by = session.get('admin_username', 'admin')
    order.refund_approved_at = datetime.utcnow()
    if admin_notes:
        order.refund_admin_notes = admin_notes

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'refund_approved')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 退款申请已批准', 'success')

    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/reject_refund', methods=['POST'])
@admin_required
def reject_refund(order_id):
    """拒绝退款申请"""
    order = Order.query.get_or_404(order_id)

    if order.refund_status != 'pending':
        flash('退款状态不允许拒绝', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    admin_notes = request.form.get('admin_notes', '').strip()
    if not admin_notes:
        flash('请填写拒绝原因', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    order.refund_status = 'rejected'
    order.refund_approved_by = session.get('admin_username', 'admin')
    order.refund_approved_at = datetime.utcnow()
    order.refund_admin_notes = admin_notes

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'refund_rejected')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 退款申请已拒绝', 'warning')

    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/order/<int:order_id>/complete_refund', methods=['POST'])
@admin_required
def complete_refund(order_id):
    """完成退款（标记为已打款）"""
    order = Order.query.get_or_404(order_id)

    if order.refund_status != 'approved':
        flash('只有已批准的退款才能标记为完成', 'error')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    order.refund_status = 'completed'
    order.refund_completed_at = datetime.utcnow()
    order.status = 'refunded'  # 更新订单状态为已退款

    db.session.commit()

    # 发送推送通知
    try:
        pushdeer_service.send_order_notification(order, 'refund_completed')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单 {order_id} 退款已完成', 'success')

    return redirect(url_for('admin.order_detail', order_id=order_id))

@bp.route('/products')
@admin_required
def products():
    """饮品产品管理"""
    page = request.args.get('page', 1, type=int)
    products = DrinkProduct.query.paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('admin/products.html', products=products)

@bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """添加新产品"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        category_id = request.form.get('category_id')
        size_options = request.form.get('size_options')
        temperature_options = request.form.get('temperature_options')

        # 处理图片上传
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                image_path = save_uploaded_file(file)

        # 获取分类名称作为备用
        category_name = None
        if category_id:
            category_obj = Category.query.get(category_id)
            if category_obj:
                category_name = category_obj.name

        product = DrinkProduct(
            name=name,
            description=description,
            price=price,
            category_id=int(category_id) if category_id else None,
            category=category_name,
            image=image_path,
            size_options=size_options,
            temperature_options=temperature_options
        )

        db.session.add(product)
        db.session.commit()
        flash(f'产品 "{name}" 添加成功', 'success')
        return redirect(url_for('admin.products'))

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template('admin/product_form.html', product=None, action='添加', categories=categories)

@bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """编辑产品"""
    product = DrinkProduct.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price', 0))

        category_id = request.form.get('category_id')
        product.category_id = int(category_id) if category_id else None

        # 处理图片上传
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                # 删除旧图片
                if product.image:
                    delete_uploaded_file(product.image)
                # 保存新图片
                product.image = save_uploaded_file(file)

        # 更新分类名称作为备用
        if category_id:
            category_obj = Category.query.get(category_id)
            if category_obj:
                product.category = category_obj.name
        else:
            product.category = None

        product.size_options = request.form.get('size_options')
        product.temperature_options = request.form.get('temperature_options')
        product.is_active = 'is_active' in request.form

        db.session.commit()
        flash(f'产品 "{product.name}" 更新成功', 'success')
        return redirect(url_for('admin.products'))

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template('admin/product_form.html', product=product, action='编辑', categories=categories)

@bp.route('/product/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    """删除产品"""
    product = DrinkProduct.query.get_or_404(product_id)

    # 检查是否有相关订单
    order_count = OrderItem.query.filter_by(drink_product_id=product_id).count()
    if order_count > 0:
        flash(f'无法删除产品 "{product.name}"，因为存在相关订单记录', 'error')
    else:
        name = product.name
        # 删除关联的图片文件
        if product.image:
            delete_uploaded_file(product.image)
        db.session.delete(product)
        db.session.commit()
        flash(f'产品 "{name}" 删除成功', 'success')

    return redirect(url_for('admin.products'))

@bp.route('/product/<int:product_id>/toggle', methods=['POST'])
@admin_required
def toggle_product_status(product_id):
    """切换产品启用/禁用状态"""
    product = DrinkProduct.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()

    status = '启用' if product.is_active else '禁用'
    flash(f'产品 "{product.name}" 已{status}', 'success')
    return redirect(url_for('admin.products'))

# 分类管理路由
@bp.route('/categories')
@admin_required
def categories():
    """分类管理"""
    page = request.args.get('page', 1, type=int)
    categories_pagination = Category.query.order_by(Category.sort_order, Category.created_at).paginate(
        page=page, per_page=10, error_out=False
    )

    # 为每个分类添加产品数量
    for category in categories_pagination.items:
        category.product_count = DrinkProduct.query.filter_by(category_id=category.id).count()

    return render_template('admin/categories.html', categories=categories_pagination)

@bp.route('/category/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    """添加新分类"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        sort_order = int(request.form.get('sort_order', 0))

        # 检查分类名称是否已存在
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            flash(f'分类 "{name}" 已存在', 'error')
        else:
            category = Category(
                name=name,
                description=description,
                sort_order=sort_order
            )

            db.session.add(category)
            db.session.commit()
            flash(f'分类 "{name}" 添加成功', 'success')
            return redirect(url_for('admin.categories'))

    return render_template('admin/category_form.html', category=None, action='添加')

@bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """编辑分类"""
    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        name = request.form.get('name')

        # 检查分类名称是否已存在（排除当前分类）
        existing_category = Category.query.filter(Category.name == name, Category.id != category_id).first()
        if existing_category:
            flash(f'分类 "{name}" 已存在', 'error')
        else:
            category.name = name
            category.description = request.form.get('description')
            category.sort_order = int(request.form.get('sort_order', 0))
            category.is_active = 'is_active' in request.form

            db.session.commit()
            flash(f'分类 "{category.name}" 更新成功', 'success')
            return redirect(url_for('admin.categories'))

    # 获取关联产品
    category.related_products = DrinkProduct.query.filter_by(category_id=category.id).all()

    return render_template('admin/category_form.html', category=category, action='编辑')

@bp.route('/category/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    """删除分类"""
    category = Category.query.get_or_404(category_id)

    # 检查是否有相关产品
    product_count = DrinkProduct.query.filter_by(category_id=category_id).count()
    if product_count > 0:
        flash(f'无法删除分类 "{category.name}"，因为存在 {product_count} 个相关产品', 'error')
    else:
        name = category.name
        db.session.delete(category)
        db.session.commit()
        flash(f'分类 "{name}" 删除成功', 'success')

    return redirect(url_for('admin.categories'))

@bp.route('/category/<int:category_id>/toggle', methods=['POST'])
@admin_required
def toggle_category_status(category_id):
    """切换分类启用/禁用状态"""
    category = Category.query.get_or_404(category_id)
    category.is_active = not category.is_active
    db.session.commit()

    status = '启用' if category.is_active else '禁用'
    flash(f'分类 "{category.name}" 已{status}', 'success')
    return redirect(url_for('admin.categories'))

# 客户管理路由
@bp.route('/customers')
@admin_required
def customers():
    """客户管理"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = User.query
    if search:
        query = query.filter(
            User.username.contains(search) |
            User.email.contains(search) |
            User.phone.contains(search)
        )

    customers = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    # 更新客户统计信息
    for customer in customers.items:
        customer.update_order_stats()
    db.session.commit()

    return render_template('admin/customers.html', customers=customers, search=search)

@bp.route('/customer/<int:customer_id>')
@admin_required
def customer_detail(customer_id):
    """客户详情"""
    customer = User.query.get_or_404(customer_id)
    customer.update_order_stats()
    db.session.commit()

    # 获取客户的订单历史
    orders = Order.query.filter_by(user_id=customer_id).order_by(Order.created_at.desc()).all()

    return render_template('admin/customer_detail.html', customer=customer, orders=orders)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """简化的管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 简化验证，实际应该有更安全的验证
        if username == 'admin' and password == 'admin123':
            session['admin_username'] = username
            session['is_admin'] = True
            flash('登录成功', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('admin/login.html')

@bp.route('/logout')
def logout():
    """管理员登出"""
    session.pop('admin_username', None)
    session.pop('is_admin', None)
    flash('已退出登录', 'info')
    return redirect(url_for('admin.login'))


# PushDeer推送配置管理路由
@bp.route('/pushdeer')
@admin_required
def pushdeer_configs():
    """PushDeer配置管理"""
    page = request.args.get('page', 1, type=int)
    configs = PushDeerConfig.query.order_by(PushDeerConfig.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('admin/pushdeer_configs.html', configs=configs)


@bp.route('/pushdeer/add', methods=['GET', 'POST'])
@admin_required
def add_pushdeer_config():
    """添加PushDeer配置"""
    if request.method == 'POST':
        name = request.form.get('name')
        pushkey = request.form.get('pushkey')
        endpoint = request.form.get('endpoint', 'https://api2.pushdeer.com')
        description = request.form.get('description')

        # 事件配置
        events_config = {
            'new_order': 'new_order' in request.form,
            'order_confirmed': 'order_confirmed' in request.form,
            'order_cancelled': 'order_cancelled' in request.form,
            'order_refunded': 'order_refunded' in request.form,
        }

        # 检查配置名称是否已存在
        existing_config = PushDeerConfig.query.filter_by(name=name).first()
        if existing_config:
            flash(f'配置名称 "{name}" 已存在', 'error')
        else:
            config = PushDeerConfig(
                name=name,
                pushkey=pushkey,
                endpoint=endpoint,
                description=description
            )
            config.set_events_config(events_config)

            db.session.add(config)
            db.session.commit()
            flash(f'PushDeer配置 "{name}" 添加成功', 'success')
            return redirect(url_for('admin.pushdeer_configs'))

    return render_template('admin/pushdeer_form.html', config=None, action='添加')


@bp.route('/pushdeer/<int:config_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_pushdeer_config(config_id):
    """编辑PushDeer配置"""
    config = PushDeerConfig.query.get_or_404(config_id)

    if request.method == 'POST':
        name = request.form.get('name')

        # 检查配置名称是否已存在（排除当前配置）
        existing_config = PushDeerConfig.query.filter(
            PushDeerConfig.name == name,
            PushDeerConfig.id != config_id
        ).first()

        if existing_config:
            flash(f'配置名称 "{name}" 已存在', 'error')
        else:
            config.name = name
            config.pushkey = request.form.get('pushkey')
            config.endpoint = request.form.get('endpoint', 'https://api2.pushdeer.com')
            config.description = request.form.get('description')
            config.is_active = 'is_active' in request.form

            # 事件配置
            events_config = {
                'new_order': 'new_order' in request.form,
                'order_confirmed': 'order_confirmed' in request.form,
                'order_cancelled': 'order_cancelled' in request.form,
                'order_refunded': 'order_refunded' in request.form,
            }
            config.set_events_config(events_config)

            db.session.commit()
            flash(f'PushDeer配置 "{config.name}" 更新成功', 'success')
            return redirect(url_for('admin.pushdeer_configs'))

    return render_template('admin/pushdeer_form.html', config=config, action='编辑')


@bp.route('/pushdeer/<int:config_id>/delete', methods=['POST'])
@admin_required
def delete_pushdeer_config(config_id):
    """删除PushDeer配置"""
    config = PushDeerConfig.query.get_or_404(config_id)
    config_name = config.name

    db.session.delete(config)
    db.session.commit()
    flash(f'PushDeer配置 "{config_name}" 已删除', 'success')
    return redirect(url_for('admin.pushdeer_configs'))


@bp.route('/pushdeer/<int:config_id>/test', methods=['POST'])
@admin_required
def test_pushdeer_config(config_id):
    """测试PushDeer配置"""
    result = pushdeer_service.test_config(config_id)

    if result['success']:
        flash('测试推送发送成功！请检查您的设备是否收到消息。', 'success')
    else:
        flash(f'测试推送失败：{result["error"]}', 'error')

    return redirect(url_for('admin.pushdeer_configs'))


@bp.route('/pushdeer/test_key', methods=['POST'])
@admin_required
def test_pushdeer_key():
    """测试PushDeer密钥"""
    pushkey = request.form.get('pushkey')
    endpoint = request.form.get('endpoint', 'https://api2.pushdeer.com')

    if not pushkey:
        return {'success': False, 'error': '请输入PushKey'}

    result = pushdeer_service.test_key(pushkey, endpoint)
    return result


# 推送记录管理路由
@bp.route('/push_records')
@admin_required
def push_records():
    """推送记录列表"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    event_filter = request.args.get('event', '')
    config_filter = request.args.get('config', '', type=int)

    # 构建查询
    query = PushRecord.query

    if status_filter:
        query = query.filter(PushRecord.status == status_filter)

    if event_filter:
        query = query.filter(PushRecord.event_type == event_filter)

    if config_filter:
        query = query.filter(PushRecord.config_id == config_filter)

    records = query.order_by(PushRecord.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # 获取筛选选项
    configs = PushDeerConfig.query.all()

    return render_template('admin/push_records.html',
                         records=records,
                         configs=configs,
                         status_filter=status_filter,
                         event_filter=event_filter,
                         config_filter=config_filter)


@bp.route('/push_records/<int:record_id>')
@admin_required
def push_record_detail(record_id):
    """推送记录详情"""
    record = PushRecord.query.get_or_404(record_id)
    return render_template('admin/push_record_detail.html', record=record)


@bp.route('/push_records/<int:record_id>/delete', methods=['POST'])
@admin_required
def delete_push_record(record_id):
    """删除推送记录"""
    record = PushRecord.query.get_or_404(record_id)

    db.session.delete(record)
    db.session.commit()
    flash('推送记录已删除', 'success')
    return redirect(url_for('admin.push_records'))


@bp.route('/push_records/clear', methods=['POST'])
@admin_required
def clear_push_records():
    """清空推送记录"""
    days = request.form.get('days', 30, type=int)

    if days > 0:
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = PushRecord.query.filter(PushRecord.created_at < cutoff_date).delete()
    else:
        deleted_count = PushRecord.query.delete()

    db.session.commit()
    flash(f'已清理 {deleted_count} 条推送记录', 'success')
    return redirect(url_for('admin.push_records'))

# 打印管理相关路由
@bp.route('/print_management')
@admin_required
def print_management():
    """打印管理页面"""
    # 获取今日订单统计
    from datetime import date
    today = date.today()

    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today
    ).all()

    pending_orders = Order.query.filter_by(status='pending').all()
    confirmed_orders = Order.query.filter_by(status='confirmed').all()

    return render_template('admin/print_management.html',
                         today_orders=today_orders,
                         pending_orders=pending_orders,
                         confirmed_orders=confirmed_orders)

@bp.route('/print_order/<int:order_id>')
@admin_required
def print_order(order_id):
    """打印单个订单"""
    order = Order.query.get_or_404(order_id)
    response = make_response(render_template('admin/print_order.html', order=order))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@bp.route('/print_daily_summary')
@admin_required
def print_daily_summary():
    """打印日报表"""
    from datetime import date
    today = date.today()

    # 获取今日订单
    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today
    ).all()

    # 统计数据
    total_orders = len(today_orders)
    total_amount = sum(order.total_amount for order in today_orders)
    pending_count = len([o for o in today_orders if o.status == 'pending'])
    confirmed_count = len([o for o in today_orders if o.status == 'confirmed'])
    rejected_count = len([o for o in today_orders if o.status == 'rejected'])
    refunded_count = len([o for o in today_orders if o.status == 'refunded'])

    # 产品销量统计
    product_stats = {}
    for order in today_orders:
        if order.status in ['confirmed', 'pending']:  # 只统计有效订单
            for item in order.order_items:
                product_name = item.drink_product.name
                if product_name not in product_stats:
                    product_stats[product_name] = {'quantity': 0, 'amount': 0}
                product_stats[product_name]['quantity'] += item.quantity
                product_stats[product_name]['amount'] += item.subtotal

    response = make_response(render_template('admin/print_daily_summary.html',
                                           today=today,
                                           today_orders=today_orders,
                                           total_orders=total_orders,
                                           total_amount=total_amount,
                                           pending_count=pending_count,
                                           confirmed_count=confirmed_count,
                                           rejected_count=rejected_count,
                                           refunded_count=refunded_count,
                                           product_stats=product_stats))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@bp.route('/print_batch_orders')
@admin_required
def print_batch_orders():
    """批量打印订单"""
    order_ids = request.args.get('order_ids', '')
    if not order_ids:
        flash('请选择要打印的订单', 'warning')
        return redirect(url_for('admin.print_management'))

    try:
        order_id_list = [int(id.strip()) for id in order_ids.split(',') if id.strip()]
        orders = Order.query.filter(Order.id.in_(order_id_list)).all()

        response = make_response(render_template('admin/print_batch_orders.html', orders=orders))
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    except ValueError:
        flash('订单ID格式错误', 'error')
        return redirect(url_for('admin.print_management'))

@bp.route('/print_receipt/<int:order_id>')
@admin_required
def print_receipt(order_id):
    """打印收据"""
    order = Order.query.get_or_404(order_id)
    response = make_response(render_template('admin/print_receipt.html', order=order))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@bp.route('/print_kitchen_ticket/<int:order_id>')
@admin_required
def print_kitchen_ticket(order_id):
    """打印制作小票"""
    order = Order.query.get_or_404(order_id)
    response = make_response(render_template('admin/print_kitchen_ticket.html', order=order))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@bp.route('/print_batch_kitchen_tickets')
@admin_required
def print_batch_kitchen_tickets():
    """批量打印制作小票"""
    order_ids = request.args.get('order_ids', '')
    if not order_ids:
        flash('请选择要打印的订单', 'warning')
        return redirect(url_for('admin.print_management'))

    try:
        order_id_list = [int(id.strip()) for id in order_ids.split(',') if id.strip()]
        orders = Order.query.filter(Order.id.in_(order_id_list)).all()

        response = make_response(render_template('admin/print_batch_kitchen_tickets.html', orders=orders))
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    except ValueError:
        flash('订单ID格式错误', 'error')
        return redirect(url_for('admin.print_management'))

# 打印机接口路由
@bp.route('/api/print_kitchen_ticket/<int:order_id>')
@admin_required
def api_print_kitchen_ticket(order_id):
    """API接口：打印制作小票"""
    printer_type = request.args.get('printer_type', 'kitchen')
    result = printer_service.print_kitchen_ticket(order_id, printer_type)

    if result['success']:
        flash(f'制作小票打印成功: {result["message"]}', 'success')
    else:
        flash(f'制作小票打印失败: {result["error"]}', 'error')

    return redirect(request.referrer or url_for('admin.print_management'))

@bp.route('/api/print_receipt/<int:order_id>')
@admin_required
def api_print_receipt(order_id):
    """API接口：打印收据"""
    printer_type = request.args.get('printer_type', 'receipt')
    result = printer_service.print_receipt(order_id, printer_type)

    if result['success']:
        flash(f'收据打印成功: {result["message"]}', 'success')
    else:
        flash(f'收据打印失败: {result["error"]}', 'error')

    return redirect(request.referrer or url_for('admin.print_management'))

@bp.route('/api/print_order/<int:order_id>')
@admin_required
def api_print_order(order_id):
    """API接口：打印订单详情"""
    printer_type = request.args.get('printer_type', 'receipt')
    result = printer_service.print_order_detail(order_id, printer_type)

    if result['success']:
        flash(f'订单详情打印成功: {result["message"]}', 'success')
    else:
        flash(f'订单详情打印失败: {result["error"]}', 'error')

    return redirect(request.referrer or url_for('admin.print_management'))

@bp.route('/api/batch_print_kitchen_tickets')
@admin_required
def api_batch_print_kitchen_tickets():
    """API接口：批量打印制作小票"""
    order_ids = request.args.get('order_ids', '')
    printer_type = request.args.get('printer_type', 'kitchen')

    if not order_ids:
        flash('请选择要打印的订单', 'warning')
        return redirect(url_for('admin.print_management'))

    try:
        order_id_list = [int(id.strip()) for id in order_ids.split(',') if id.strip()]
        success_count = 0
        error_count = 0

        for order_id in order_id_list:
            result = printer_service.print_kitchen_ticket(order_id, printer_type)
            if result['success']:
                success_count += 1
            else:
                error_count += 1

        if error_count == 0:
            flash(f'批量打印成功: {success_count} 个制作小票', 'success')
        else:
            flash(f'批量打印完成: 成功 {success_count} 个，失败 {error_count} 个', 'warning')

    except ValueError:
        flash('订单ID格式错误', 'error')

    return redirect(request.referrer or url_for('admin.print_management'))

# 公告管理路由
@bp.route('/announcements')
@admin_required
def announcements():
    """公告管理页面"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    announcement_type = request.args.get('type', '')
    status = request.args.get('status', '')

    query = Announcement.query

    # 搜索功能
    if search:
        query = query.filter(
            db.or_(
                Announcement.title.contains(search),
                Announcement.content.contains(search)
            )
        )

    # 类型筛选
    if announcement_type:
        query = query.filter(Announcement.announcement_type == announcement_type)

    # 状态筛选
    if status == 'active':
        query = query.filter(Announcement.is_active == True)
    elif status == 'inactive':
        query = query.filter(Announcement.is_active == False)

    # 按优先级和创建时间排序
    query = query.order_by(Announcement.priority.desc(), Announcement.created_at.desc())

    announcements = query.paginate(
        page=page, per_page=10, error_out=False
    )

    # 统计数据
    active_count = Announcement.query.filter_by(is_active=True).count()
    homepage_count = Announcement.query.filter_by(show_on_homepage=True).count()
    now = datetime.utcnow()
    expired_count = Announcement.query.filter(
        Announcement.end_time < now
    ).count()

    # 检查是否使用Element UI版本
    use_element = request.args.get('ui') == 'element'

    template_data = {
        'announcements': announcements,
        'search': search,
        'type_filter': announcement_type,
        'status_filter': status,
        'active_count': active_count,
        'homepage_count': homepage_count,
        'expired_count': expired_count
    }

    if use_element:
        return render_template('admin/element_announcements.html', **template_data)
    else:
        return render_template('admin/announcements.html', **template_data)

@bp.route('/announcements/add', methods=['GET', 'POST'])
@admin_required
def add_announcement():
    """添加公告"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('announcement_type', 'info')
        priority = request.form.get('priority', 0, type=int)
        is_active = request.form.get('is_active') == 'on'
        show_on_homepage = request.form.get('show_on_homepage') == 'on'
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template('admin/add_announcement.html')

        announcement = Announcement(
            title=title,
            content=content,
            announcement_type=announcement_type,
            priority=priority,
            is_active=is_active,
            show_on_homepage=show_on_homepage,
            created_by=session.get('user_id')
        )

        # 处理时间
        if start_time:
            try:
                announcement.start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        if end_time:
            try:
                announcement.end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        db.session.add(announcement)
        db.session.commit()

        flash('公告添加成功', 'success')
        return redirect(url_for('admin.announcements'))

    # 检查是否使用Element UI版本
    use_element = request.args.get('ui') == 'element'

    if use_element:
        return render_template('admin/element_add_announcement.html')
    else:
        return render_template('admin/add_announcement.html')

@bp.route('/announcements/edit/<int:announcement_id>', methods=['GET', 'POST'])
@admin_required
def edit_announcement(announcement_id):
    """编辑公告"""
    announcement = Announcement.query.get_or_404(announcement_id)

    if request.method == 'POST':
        announcement.title = request.form.get('title')
        announcement.content = request.form.get('content')
        announcement.announcement_type = request.form.get('announcement_type', 'info')
        announcement.priority = request.form.get('priority', 0, type=int)
        announcement.is_active = request.form.get('is_active') == 'on'
        announcement.show_on_homepage = request.form.get('show_on_homepage') == 'on'

        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not announcement.title or not announcement.content:
            flash('标题和内容不能为空', 'error')
            return render_template('admin/edit_announcement.html', announcement=announcement)

        # 处理时间
        if start_time:
            try:
                announcement.start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                announcement.start_time = None
        else:
            announcement.start_time = None

        if end_time:
            try:
                announcement.end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                announcement.end_time = None
        else:
            announcement.end_time = None

        announcement.updated_at = datetime.utcnow()
        db.session.commit()

        flash('公告更新成功', 'success')
        return redirect(url_for('admin.announcements'))

    return render_template('admin/edit_announcement.html', announcement=announcement)

@bp.route('/announcements/delete/<int:announcement_id>')
@admin_required
def delete_announcement(announcement_id):
    """删除公告"""
    announcement = Announcement.query.get_or_404(announcement_id)

    db.session.delete(announcement)
    db.session.commit()

    flash('公告删除成功', 'success')
    return redirect(url_for('admin.announcements'))

@bp.route('/announcements/toggle/<int:announcement_id>')
@admin_required
def toggle_announcement(announcement_id):
    """切换公告状态"""
    announcement = Announcement.query.get_or_404(announcement_id)

    announcement.is_active = not announcement.is_active
    announcement.updated_at = datetime.utcnow()
    db.session.commit()

    status = '启用' if announcement.is_active else '禁用'
    flash(f'公告已{status}', 'success')
    return redirect(url_for('admin.announcements'))

# 菜单管理路由
@bp.route('/menu_config')
@admin_required
def menu_config():
    """菜单配置管理"""
    menus = MenuConfig.query.order_by(MenuConfig.sort_order).all()
    return render_template('admin/menu_config.html', menus=menus)

@bp.route('/menu_config/init')
@admin_required
def init_menu_config():
    """初始化默认菜单配置"""
    # 检查是否已有菜单配置
    if MenuConfig.query.count() > 0:
        flash('菜单配置已存在，无需初始化', 'info')
        return redirect(url_for('admin.menu_config'))

    # 默认菜单配置
    default_menus = [
        {'key': 'dashboard', 'name': '仪表盘', 'icon': 'fas fa-tachometer-alt', 'url': 'admin.dashboard', 'sort': 1},
        {'key': 'orders', 'name': '订单管理', 'icon': 'fas fa-shopping-cart', 'url': 'admin.orders', 'sort': 2},
        {'key': 'customers', 'name': '客户管理', 'icon': 'fas fa-users', 'url': 'admin.customers', 'sort': 3},
        {'key': 'categories', 'name': '分类管理', 'icon': 'fas fa-tags', 'url': 'admin.categories', 'sort': 4},
        {'key': 'products', 'name': '产品管理', 'icon': 'fas fa-coffee', 'url': 'admin.products', 'sort': 5},
        {'key': 'pushdeer', 'name': '推送设置', 'icon': 'fas fa-bell', 'url': 'admin.pushdeer_configs', 'sort': 6},
        {'key': 'push_records', 'name': '推送记录', 'icon': 'fas fa-history', 'url': 'admin.push_records', 'sort': 7},
        {'key': 'print_mgmt', 'name': '打印管理', 'icon': 'fas fa-print', 'url': 'admin.print_management', 'sort': 8},
        {'key': 'announcements', 'name': '首页公告', 'icon': 'fas fa-bullhorn', 'url': 'admin.announcements', 'sort': 9},
        {'key': 'menu_config', 'name': '菜单排序', 'icon': 'fas fa-sort', 'url': 'admin.menu_config', 'sort': 10},
    ]

    try:
        for menu_data in default_menus:
            menu = MenuConfig(
                menu_key=menu_data['key'],
                menu_name=menu_data['name'],
                menu_icon=menu_data['icon'],
                menu_url=menu_data['url'],
                sort_order=menu_data['sort']
            )
            db.session.add(menu)

        db.session.commit()
        flash('菜单配置初始化成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'菜单配置初始化失败: {str(e)}', 'error')

    return redirect(url_for('admin.menu_config'))

@bp.route('/menu_config/update_order', methods=['POST'])
@admin_required
def update_menu_order():
    """更新菜单排序"""
    try:
        data = request.get_json()
        menu_orders = data.get('menu_orders', [])

        for item in menu_orders:
            menu_id = item.get('id')
            sort_order = item.get('sort_order')

            menu = MenuConfig.query.get(menu_id)
            if menu:
                menu.sort_order = sort_order

        db.session.commit()
        return jsonify({'success': True, 'message': '菜单排序更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@bp.route('/menu_config/<int:menu_id>/toggle')
@admin_required
def toggle_menu_visibility(menu_id):
    """切换菜单显示状态"""
    menu = MenuConfig.query.get_or_404(menu_id)
    menu.is_visible = not menu.is_visible
    db.session.commit()

    status = '显示' if menu.is_visible else '隐藏'
    flash(f'菜单"{menu.menu_name}"已设置为{status}', 'success')
    return redirect(url_for('admin.menu_config'))

# 管理员管理路由
@bp.route('/admin_users')
@admin_required
def admin_users():
    """管理员用户管理"""
    page = request.args.get('page', 1, type=int)
    users = AdminUser.query.order_by(AdminUser.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/admin_users.html', users=users)

@bp.route('/admin_users/create', methods=['GET', 'POST'])
@admin_required
def create_admin_user():
    """创建管理员用户"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            real_name = request.form.get('real_name')
            phone = request.form.get('phone')
            is_super_admin = request.form.get('is_super_admin') == 'on'
            role_ids = request.form.getlist('roles')

            # 检查用户名和邮箱是否已存在
            if AdminUser.query.filter_by(username=username).first():
                flash('用户名已存在', 'error')
                return redirect(url_for('admin.create_admin_user'))

            if AdminUser.query.filter_by(email=email).first():
                flash('邮箱已存在', 'error')
                return redirect(url_for('admin.create_admin_user'))

            # 创建管理员用户
            admin_user = AdminUser(
                username=username,
                email=email,
                real_name=real_name,
                phone=phone,
                is_super_admin=is_super_admin
            )
            admin_user.set_password(password)

            # 分配角色
            if role_ids:
                roles = AdminRole.query.filter(AdminRole.id.in_(role_ids)).all()
                admin_user.roles = roles

            db.session.add(admin_user)
            db.session.commit()

            flash('管理员用户创建成功', 'success')
            return redirect(url_for('admin.admin_users'))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')

    # 获取所有角色
    roles = AdminRole.query.filter_by(is_active=True).all()
    return render_template('admin/create_admin_user.html', roles=roles)

@bp.route('/admin_users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_admin_user(user_id):
    """编辑管理员用户"""
    admin_user = AdminUser.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            admin_user.real_name = request.form.get('real_name')
            admin_user.phone = request.form.get('phone')
            admin_user.is_super_admin = request.form.get('is_super_admin') == 'on'

            # 更新密码（如果提供）
            new_password = request.form.get('password')
            if new_password:
                admin_user.set_password(new_password)

            # 更新角色
            role_ids = request.form.getlist('roles')
            if role_ids:
                roles = AdminRole.query.filter(AdminRole.id.in_(role_ids)).all()
                admin_user.roles = roles
            else:
                admin_user.roles = []

            db.session.commit()
            flash('管理员用户更新成功', 'success')
            return redirect(url_for('admin.admin_users'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    roles = AdminRole.query.filter_by(is_active=True).all()
    return render_template('admin/edit_admin_user.html', admin_user=admin_user, roles=roles)

@bp.route('/admin_users/<int:user_id>/toggle')
@admin_required
def toggle_admin_user(user_id):
    """切换管理员用户状态"""
    admin_user = AdminUser.query.get_or_404(user_id)
    admin_user.is_active = not admin_user.is_active
    db.session.commit()

    status = '启用' if admin_user.is_active else '禁用'
    flash(f'管理员"{admin_user.username}"已{status}', 'success')
    return redirect(url_for('admin.admin_users'))

# 角色管理路由
@bp.route('/admin_roles')
@admin_required
def admin_roles():
    """角色管理"""
    roles = AdminRole.query.order_by(AdminRole.created_at.desc()).all()
    return render_template('admin/admin_roles.html', roles=roles)

@bp.route('/admin_roles/create', methods=['GET', 'POST'])
@admin_required
def create_admin_role():
    """创建角色"""
    if request.method == 'POST':
        try:
            role_name = request.form.get('role_name')
            role_code = request.form.get('role_code')
            description = request.form.get('description')
            permission_ids = request.form.getlist('permissions')

            # 检查角色代码是否已存在
            if AdminRole.query.filter_by(role_code=role_code).first():
                flash('角色代码已存在', 'error')
                return redirect(url_for('admin.create_admin_role'))

            # 创建角色
            role = AdminRole(
                role_name=role_name,
                role_code=role_code,
                description=description
            )

            # 分配权限
            if permission_ids:
                permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
                role.permissions = permissions

            db.session.add(role)
            db.session.commit()

            flash('角色创建成功', 'success')
            return redirect(url_for('admin.admin_roles'))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')

    permissions = Permission.query.filter_by(is_active=True).order_by(Permission.module, Permission.permission_name).all()
    return render_template('admin/create_admin_role.html', permissions=permissions)

@bp.route('/admin_roles/<int:role_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_admin_role(role_id):
    """编辑角色"""
    role = AdminRole.query.get_or_404(role_id)

    if request.method == 'POST':
        try:
            role.role_name = request.form.get('role_name')
            role.description = request.form.get('description')

            # 更新权限
            permission_ids = request.form.getlist('permissions')
            if permission_ids:
                permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
                role.permissions = permissions
            else:
                role.permissions = []

            db.session.commit()
            flash('角色更新成功', 'success')
            return redirect(url_for('admin.admin_roles'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    permissions = Permission.query.filter_by(is_active=True).order_by(Permission.module, Permission.permission_name).all()
    return render_template('admin/edit_admin_role.html', role=role, permissions=permissions)

# 权限管理路由
@bp.route('/permissions')
@admin_required
def permissions():
    """权限管理"""
    permissions = Permission.query.order_by(Permission.module, Permission.permission_name).all()

    # 按模块分组
    grouped_permissions = {}
    for permission in permissions:
        if permission.module not in grouped_permissions:
            grouped_permissions[permission.module] = []
        grouped_permissions[permission.module].append(permission)

    return render_template('admin/permissions.html', grouped_permissions=grouped_permissions)

@bp.route('/permissions/init')
@admin_required
def init_permissions():
    """初始化默认权限"""
    if Permission.query.count() > 0:
        flash('权限已存在，无需初始化', 'info')
        return redirect(url_for('admin.permissions'))

    # 默认权限配置
    default_permissions = [
        # 订单管理
        {'name': '查看订单', 'code': 'order.view', 'module': '订单管理'},
        {'name': '编辑订单', 'code': 'order.edit', 'module': '订单管理'},
        {'name': '删除订单', 'code': 'order.delete', 'module': '订单管理'},
        {'name': '确认订单', 'code': 'order.confirm', 'module': '订单管理'},
        {'name': '拒绝订单', 'code': 'order.reject', 'module': '订单管理'},

        # 客户管理
        {'name': '查看客户', 'code': 'customer.view', 'module': '客户管理'},
        {'name': '编辑客户', 'code': 'customer.edit', 'module': '客户管理'},
        {'name': '删除客户', 'code': 'customer.delete', 'module': '客户管理'},

        # 产品管理
        {'name': '查看产品', 'code': 'product.view', 'module': '产品管理'},
        {'name': '添加产品', 'code': 'product.create', 'module': '产品管理'},
        {'name': '编辑产品', 'code': 'product.edit', 'module': '产品管理'},
        {'name': '删除产品', 'code': 'product.delete', 'module': '产品管理'},

        # 分类管理
        {'name': '查看分类', 'code': 'category.view', 'module': '分类管理'},
        {'name': '添加分类', 'code': 'category.create', 'module': '分类管理'},
        {'name': '编辑分类', 'code': 'category.edit', 'module': '分类管理'},
        {'name': '删除分类', 'code': 'category.delete', 'module': '分类管理'},

        # 系统管理
        {'name': '管理员管理', 'code': 'admin.manage', 'module': '系统管理'},
        {'name': '角色管理', 'code': 'role.manage', 'module': '系统管理'},
        {'name': '权限管理', 'code': 'permission.manage', 'module': '系统管理'},
        {'name': '菜单管理', 'code': 'menu.manage', 'module': '系统管理'},
        {'name': '推送管理', 'code': 'push.manage', 'module': '系统管理'},
        {'name': '公告管理', 'code': 'announcement.manage', 'module': '系统管理'},
    ]

    try:
        for perm_data in default_permissions:
            permission = Permission(
                permission_name=perm_data['name'],
                permission_code=perm_data['code'],
                module=perm_data['module']
            )
            db.session.add(permission)

        db.session.commit()
        flash('权限初始化成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'权限初始化失败: {str(e)}', 'error')

    return redirect(url_for('admin.permissions'))

# 收款码管理路由
@bp.route('/payment_config')
@admin_required
def payment_config():
    """收款码配置管理"""
    payments = PaymentConfig.query.order_by(PaymentConfig.sort_order).all()
    return render_template('admin/payment_config.html', payments=payments)

@bp.route('/payment_config/create', methods=['GET', 'POST'])
@admin_required
def create_payment_config():
    """创建收款码配置"""
    if request.method == 'POST':
        try:
            payment_type = request.form.get('payment_type')
            payment_name = request.form.get('payment_name')
            qr_code_url = request.form.get('qr_code_url')
            account_name = request.form.get('account_name')
            account_info = request.form.get('account_info')
            sort_order = request.form.get('sort_order', 0, type=int)

            # 处理文件上传
            qr_code_path = None
            if 'qr_code_file' in request.files:
                file = request.files['qr_code_file']
                if file and file.filename:
                    import os
                    from werkzeug.utils import secure_filename

                    # 确保上传目录存在
                    upload_dir = os.path.join('static', 'uploads', 'qr_codes')
                    os.makedirs(upload_dir, exist_ok=True)

                    # 保存文件
                    filename = secure_filename(file.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    qr_code_path = f'uploads/qr_codes/{filename}'

            # 创建支付配置
            payment_config = PaymentConfig(
                payment_type=payment_type,
                payment_name=payment_name,
                qr_code_path=qr_code_path,
                qr_code_url=qr_code_url,
                account_name=account_name,
                account_info=account_info,
                sort_order=sort_order
            )

            db.session.add(payment_config)
            db.session.commit()

            flash('收款码配置创建成功', 'success')
            return redirect(url_for('admin.payment_config'))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')

    return render_template('admin/create_payment_config.html')

@bp.route('/payment_config/<int:config_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_payment_config(config_id):
    """编辑收款码配置"""
    payment_config = PaymentConfig.query.get_or_404(config_id)

    if request.method == 'POST':
        try:
            payment_config.payment_name = request.form.get('payment_name')
            payment_config.qr_code_url = request.form.get('qr_code_url')
            payment_config.account_name = request.form.get('account_name')
            payment_config.account_info = request.form.get('account_info')
            payment_config.sort_order = request.form.get('sort_order', 0, type=int)

            # 处理文件上传
            if 'qr_code_file' in request.files:
                file = request.files['qr_code_file']
                if file and file.filename:
                    import os
                    from werkzeug.utils import secure_filename

                    # 删除旧文件
                    if payment_config.qr_code_path:
                        old_file_path = os.path.join('static', payment_config.qr_code_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)

                    # 保存新文件
                    upload_dir = os.path.join('static', 'uploads', 'qr_codes')
                    os.makedirs(upload_dir, exist_ok=True)

                    filename = secure_filename(file.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    payment_config.qr_code_path = f'uploads/qr_codes/{filename}'

            db.session.commit()
            flash('收款码配置更新成功', 'success')
            return redirect(url_for('admin.payment_config'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    return render_template('admin/edit_payment_config.html', payment_config=payment_config)

@bp.route('/payment_config/<int:config_id>/toggle')
@admin_required
def toggle_payment_config(config_id):
    """切换收款码配置状态"""
    payment_config = PaymentConfig.query.get_or_404(config_id)
    payment_config.is_active = not payment_config.is_active
    db.session.commit()

    status = '启用' if payment_config.is_active else '禁用'
    flash(f'收款码"{payment_config.payment_name}"已{status}', 'success')
    return redirect(url_for('admin.payment_config'))

@bp.route('/payment_config/<int:config_id>/delete')
@admin_required
def delete_payment_config(config_id):
    """删除收款码配置"""
    payment_config = PaymentConfig.query.get_or_404(config_id)

    try:
        # 删除文件
        if payment_config.qr_code_path:
            import os
            file_path = os.path.join('static', payment_config.qr_code_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(payment_config)
        db.session.commit()

        flash(f'收款码"{payment_config.payment_name}"删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'error')

    return redirect(url_for('admin.payment_config'))
