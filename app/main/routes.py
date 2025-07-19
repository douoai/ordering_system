from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from app.main import bp
from app.main.forms import UserInfoForm, OrderForm
from app.models import db, User, DrinkProduct, Order, OrderItem, Category, Announcement
from app.services.pushdeer import pushdeer_service

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    """首页 - 显示饮品产品列表"""
    category_filter = request.args.get('category')

    if category_filter:
        drink_products = DrinkProduct.query.filter_by(is_active=True, category_id=category_filter).all()
    else:
        drink_products = DrinkProduct.query.filter_by(is_active=True).all()

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()

    # 获取首页公告
    now = datetime.utcnow()
    announcements = Announcement.query.filter(
        Announcement.is_active == True,
        Announcement.show_on_homepage == True,
        db.or_(
            Announcement.start_time.is_(None),
            Announcement.start_time <= now
        ),
        db.or_(
            Announcement.end_time.is_(None),
            Announcement.end_time >= now
        )
    ).order_by(Announcement.priority.desc(), Announcement.created_at.desc()).limit(3).all()

    return render_template('element_index.html',
                         drink_products=drink_products,
                         categories=categories,
                         current_category=category_filter,
                         announcements=announcements)

@bp.route('/user_info', methods=['GET', 'POST'])
def user_info():
    """用户信息页面 - 简化版，只需要用户名和电话"""
    form = UserInfoForm()

    # 获取产品信息（如果有product_id参数）
    product = None
    product_id = request.args.get('product_id')
    if product_id:
        try:
            product = DrinkProduct.query.get(int(product_id))
        except (ValueError, TypeError):
            pass
    if form.validate_on_submit():
        # 检查用户是否已存在（通过电话号码）
        user = User.query.filter_by(phone=form.phone.data).first()
        if not user:
            # 创建新用户，使用电话号码作为邮箱（保持数据库兼容性）
            user = User(
                username=form.username.data,
                email=f"{form.phone.data}@phone.local",  # 使用电话号码生成邮箱
                phone=form.phone.data
            )
            db.session.add(user)
        else:
            # 更新现有用户信息
            user.username = form.username.data

        db.session.commit()

        # 将用户信息存储在session中
        session['user_id'] = user.id
        session['username'] = user.username
        session['phone'] = user.phone

        flash(f'欢迎 {user.username}！', 'success')

        # 检查是否有产品ID参数，如果有则直接下单
        product_id = request.form.get('product_id') or request.args.get('product_id')
        if product_id:
            try:
                quantity = form.quantity.data if hasattr(form, 'quantity') and form.quantity.data else 1
                # 检查是否使用Element UI样式
                use_element = request.args.get('style') == 'element'
                if use_element:
                    session['use_element_ui'] = True
                return redirect(url_for('main.quick_order_with_quantity', product_id=int(product_id), quantity=quantity))
            except (ValueError, TypeError):
                pass

        return redirect(url_for('main.order'))

    # 获取当前用户信息
    user = None
    user_stats = {
        'total_orders': 0,
        'total_spent': 0.0,
        'completed_orders': 0,
        'favorite_product': None
    }

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            # 计算用户统计信息
            user_orders = Order.query.filter_by(user_id=user.id).all()
            user_stats['total_orders'] = len(user_orders)
            user_stats['completed_orders'] = len([o for o in user_orders if o.status == 'completed'])
            user_stats['total_spent'] = sum(o.total_amount for o in user_orders if o.status in ['completed', 'confirmed'])

            # 获取最喜欢的产品（简单统计）
            if user_orders:
                from collections import Counter
                product_counts = Counter()
                for order in user_orders:
                    for item in order.items:
                        product_counts[item.product_name] += item.quantity
                if product_counts:
                    user_stats['favorite_product'] = product_counts.most_common(1)[0][0]

    return render_template('element_user_info.html', form=form, product=product, user=user, user_stats=user_stats)

@bp.route('/order', methods=['GET', 'POST'])
def order():
    """下单页面"""
    if 'user_id' not in session:
        flash('请先填写用户信息', 'warning')
        return redirect(url_for('main.user_info'))
    
    form = OrderForm()
    # 填充饮品产品选择项
    drink_products = DrinkProduct.query.filter_by(is_active=True).all()
    form.drink_product_id.choices = [(p.id, f"{p.name} - ¥{p.price}") for p in drink_products]

    # 如果从首页传来了产品ID，预选该产品
    product_id = request.args.get('product_id')
    if product_id and not form.is_submitted():
        try:
            form.drink_product_id.data = int(product_id)
        except (ValueError, TypeError):
            pass

    if form.validate_on_submit():
        user_id = session['user_id']
        drink_product = DrinkProduct.query.get(form.drink_product_id.data)

        if drink_product:
            # 创建订单
            order = Order(
                user_id=user_id,
                total_amount=drink_product.price * form.quantity.data,
                notes=form.notes.data
            )
            db.session.add(order)
            db.session.flush()  # 获取订单ID

            # 创建订单项
            order_item = OrderItem(
                order_id=order.id,
                drink_product_id=drink_product.id,
                quantity=form.quantity.data,
                unit_price=drink_product.price,
                subtotal=drink_product.price * form.quantity.data,
                size=None,  # 不再使用规格
                temperature=form.temperature.data,
                notes=form.item_notes.data
            )
            db.session.add(order_item)
            db.session.commit()

            # 发送新订单推送通知
            try:
                pushdeer_service.send_order_notification(order, 'new_order')
            except Exception as e:
                print(f"推送通知失败: {e}")

            flash(f'订单提交成功！订单号：{order.id}', 'success')
            return redirect(url_for('main.order_success', order_id=order.id))

    return render_template('element_order.html', form=form, drink_products=drink_products)

@bp.route('/quick_order/<int:product_id>')
def quick_order(product_id):
    """快速下单 - 直接为指定产品创建订单（默认数量1）"""
    return quick_order_with_quantity(product_id, 1)

@bp.route('/quick_order/<int:product_id>/<int:quantity>')
def quick_order_with_quantity(product_id, quantity=1):
    """快速下单 - 直接为指定产品创建订单，支持指定数量"""
    if 'user_id' not in session:
        # 未登录用户，跳转到用户信息页面并传递产品ID
        return redirect(url_for('main.user_info', product_id=product_id))

    # 验证数量范围
    if quantity < 1 or quantity > 20:
        flash('数量必须在1-20之间', 'error')
        return redirect(url_for('main.index'))

    # 获取产品信息
    drink_product = DrinkProduct.query.get_or_404(product_id)
    user_id = session['user_id']

    # 计算总价
    total_amount = drink_product.price * quantity

    # 创建订单
    order = Order(
        user_id=user_id,
        total_amount=total_amount,
        notes=f'快速下单 - {drink_product.name} x{quantity}'
    )
    db.session.add(order)
    db.session.flush()  # 获取订单ID

    # 创建订单项
    order_item = OrderItem(
        order_id=order.id,
        drink_product_id=drink_product.id,
        quantity=quantity,
        unit_price=drink_product.price,
        subtotal=total_amount,
        size=None,
        temperature='normal',  # 默认常温
        notes=''
    )
    db.session.add(order_item)
    db.session.commit()

    # 发送新订单推送通知
    try:
        pushdeer_service.send_order_notification(order, 'new_order')
    except Exception as e:
        print(f"推送通知失败: {e}")

    flash(f'订单创建成功！订单号：{order.id}，数量：{quantity}份', 'success')
    # 直接跳转到支付页面
    return redirect(url_for('main.payment', order_id=order.id))

@bp.route('/order_success/<int:order_id>')
def order_success(order_id):
    """订单成功页面"""
    order = Order.query.get_or_404(order_id)
    return render_template('element_order_success.html', order=order)

@bp.route('/payment/<int:order_id>')
def payment(order_id):
    """支付页面"""
    order = Order.query.get_or_404(order_id)

    # 检查订单状态
    if order.status not in ['pending', 'confirmed']:
        flash('订单状态不允许支付', 'error')
        return redirect(url_for('main.order_detail', order_id=order_id))

    # 获取用户信息
    user = User.query.get_or_404(order.user_id)

    # 获取支付配置
    from app.models import PaymentConfig
    payment_configs = PaymentConfig.get_active_payments()

    return render_template('element_payment.html', order=order, user=user, payment_configs=payment_configs)

@bp.route('/confirm_payment/<int:order_id>', methods=['POST'])
def confirm_payment(order_id):
    """确认支付"""
    order = Order.query.get_or_404(order_id)

    try:
        data = request.get_json()
        if data and data.get('confirmed'):
            # 更新订单状态为已支付
            order.status = 'paid'
            order.payment_time = datetime.now()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '支付确认成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '确认信息无效'
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'确认失败: {str(e)}'
        })



@bp.route('/my_orders')
def my_orders():
    """我的订单页面"""
    # 支持通过手机号查询订单
    phone = request.args.get('phone', '').strip()

    if not phone:
        return render_template('element_my_orders.html', orders=[], phone='', show_form=True)

    # 根据手机号查找用户
    user = User.query.filter_by(phone=phone).first()
    if not user:
        flash('未找到该手机号的订单记录', 'warning')
        return render_template('element_my_orders.html', orders=[], phone=phone, show_form=True)

    # 获取用户的所有订单
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()

    return render_template('element_my_orders.html', orders=orders, phone=phone, user=user, show_form=False)

@bp.route('/quick_order_check', methods=['GET', 'POST'])
def quick_order_check():
    """快速订单查询"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if phone:
            return redirect(url_for('main.my_orders', phone=phone))
        else:
            flash('请输入手机号', 'warning')

    return render_template('element_quick_order_check.html')

@bp.route('/order/<int:order_id>')
def order_detail(order_id):
    """订单详情页面"""
    order = Order.query.get_or_404(order_id)
    user = User.query.get_or_404(order.user_id)

    # 检查是否使用Element UI样式
    return render_template('element_order_detail.html', order=order, user=user)

@bp.route('/order/<int:order_id>/refund', methods=['GET', 'POST'])
def refund_order(order_id):
    """用户申请退款"""
    order = Order.query.get_or_404(order_id)

    # 检查是否可以退款
    if not order.can_refund:
        flash('该订单不能退款。', 'error')
        return redirect(url_for('main.order_detail', order_id=order_id))

    if request.method == 'POST':
        refund_reason = request.form.get('refund_reason', '').strip()
        if not refund_reason:
            flash('请填写退款原因', 'error')
            return render_template('element_refund_order.html', order=order)

        # 检查是否需要上传二维码
        if order.needs_refund_approval:
            # 已支付订单需要上传收款二维码
            if 'refund_qr_code' not in request.files:
                flash('请上传收款二维码', 'error')
                return render_template('element_refund_order.html', order=order)

            file = request.files['refund_qr_code']
            if file.filename == '':
                flash('请选择收款二维码文件', 'error')
                return render_template('element_refund_order.html', order=order)

            if file and allowed_file(file.filename):
                # 保存二维码文件
                filename = secure_filename(file.filename)
                # 生成唯一文件名
                import uuid
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"refund_qr_{uuid.uuid4().hex[:8]}.{file_ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                # 更新订单状态为退款审核中
                order.refund_reason = refund_reason
                order.refund_qr_code = unique_filename
                order.refund_status = 'pending'
                order.refunded_at = datetime.utcnow()

                flash('退款申请已提交，请等待管理员审核', 'info')
            else:
                flash('请上传有效的图片文件（jpg, jpeg, png, gif）', 'error')
                return render_template('element_refund_order.html', order=order)
        else:
            # 待确认订单可以直接退款
            order.status = 'refunded'
            order.refund_reason = refund_reason
            order.refunded_at = datetime.utcnow()
            order.refund_status = 'completed'
            order.refund_completed_at = datetime.utcnow()

            flash('退款申请成功！', 'success')

        db.session.commit()

        # 发送退款申请推送通知
        try:
            event_type = 'refund_request' if order.needs_refund_approval else 'order_refunded'
            pushdeer_service.send_order_notification(order, event_type)
        except Exception as e:
            print(f"退款推送通知失败: {e}")

        return redirect(url_for('main.order_detail', order_id=order_id))

    # 检查是否使用Element UI样式
    return render_template('element_refund_order.html', order=order, user=user)

@bp.route('/test_upload')
def test_upload():
    """测试文件上传功能"""
    return render_template('test_upload.html')

@bp.route('/test_element_upload')
def test_element_upload():
    """测试Element UI上传功能"""
    return render_template('test_element_upload.html')

@bp.route('/element_ui_demo')
def element_ui_demo():
    """Element UI上传组件完整演示"""
    return render_template('element_ui_demo.html')

@bp.route('/test_cancel_upload')
def test_cancel_upload():
    """测试取消订单上传功能"""
    return render_template('test_cancel_upload.html')

@bp.route('/debug_element_ui')
def debug_element_ui():
    """Element UI调试页面"""
    return render_template('debug_element_ui.html')

@bp.route('/native_upload_test')
def native_upload_test():
    """原生HTML5拖拽上传测试"""
    return render_template('native_upload_test.html')

@bp.route('/test_refund_page')
def test_refund_page():
    """测试新的分区退款页面"""
    # 创建一个模拟订单用于测试
    from app.models import Order, User, DrinkProduct, OrderItem

    # 获取或创建测试用户
    user = User.query.filter_by(phone='13800138000').first()
    if not user:
        user = User(username='测试用户', email='test@example.com', phone='13800138000')
        db.session.add(user)
        db.session.flush()

    # 获取产品
    product = DrinkProduct.query.first()
    if not product:
        flash('没有可用的产品', 'error')
        return redirect(url_for('main.index'))

    # 创建测试订单
    order = Order(
        user_id=user.id,
        total_amount=35.00,
        status='paid',
        notes='测试分区退款页面',
        created_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()

    # 添加订单项
    order_item = OrderItem(
        order_id=order.id,
        drink_product_id=product.id,
        quantity=2,
        unit_price=17.50,
        subtotal=35.00,
        size='大杯',
        temperature='正常冰',
        sugar_level='正常糖',
        notes='测试商品'
    )
    db.session.add(order_item)
    db.session.commit()

    return render_template('element_refund_order.html', order=order)

@bp.route('/create_test_paid_order')
def create_test_paid_order():
    """创建一个已支付的测试订单"""
    from datetime import datetime

    # 获取用户信息
    user_id = session.get('user_id')
    if not user_id:
        # 检查是否已有测试用户
        user = User.query.filter_by(phone='13800138000').first()
        if not user:
            # 创建测试用户
            user = User(username='测试用户', email='test@example.com', phone='13800138000')
            db.session.add(user)
            db.session.flush()
        user_id = user.id
        session['user_id'] = user_id

    # 获取一个产品
    product = DrinkProduct.query.first()
    if not product:
        flash('没有可用的产品', 'error')
        return redirect(url_for('main.index'))

    # 创建订单
    order = Order(
        user_id=user_id,
        total_amount=25.00,
        status='paid',  # 设置为已支付
        notes='测试已付款订单 - 用于测试取消订单功能',
        created_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()

    # 添加订单项
    order_item = OrderItem(
        order_id=order.id,
        drink_product_id=product.id,
        quantity=1,
        unit_price=25.00,
        subtotal=25.00,
        size='大杯',
        temperature='正常冰',
        sugar_level='正常糖',
        notes='测试订单项'
    )
    db.session.add(order_item)
    db.session.commit()

    flash(f'已创建测试订单 #{order.id}，状态：已支付', 'success')
    return redirect(url_for('main.refund_order', order_id=order.id))

@bp.route('/order/<int:order_id>/cancel', methods=['GET', 'POST'])
def cancel_order(order_id):
    """取消订单"""
    order = Order.query.get_or_404(order_id)

    # 检查是否可以取消
    if not order.can_cancel:
        flash('此订单不能取消', 'error')
        return redirect(url_for('main.order_detail', order_id=order_id))

    if request.method == 'POST':
        cancel_reason = request.form.get('cancel_reason', '').strip()
        if not cancel_reason:
            flash('请填写取消原因', 'error')
            return render_template('element_cancel_order.html', order=order)

        # 检查是否需要上传收款二维码
        if order.needs_cancel_qr_code:
            cancel_qr_code = request.files.get('cancel_qr_code')
            if not cancel_qr_code or cancel_qr_code.filename == '':
                flash('已付款订单取消需要上传收款二维码', 'error')
                return render_template('element_cancel_order.html', order=order)

        # 获取当前用户（如果有登录）
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None

        try:
            # 处理文件上传（如果需要）
            qr_code_filename = None
            if order.needs_cancel_qr_code and 'cancel_qr_code' in request.files:
                cancel_qr_code = request.files['cancel_qr_code']
                if cancel_qr_code and cancel_qr_code.filename:
                    # 验证文件类型
                    if not allowed_file(cancel_qr_code.filename):
                        flash('请上传有效的图片文件（JPG、PNG、GIF）', 'error')
                        return render_template('element_cancel_order.html', order=order)

                    # 保存文件
                    filename = secure_filename(cancel_qr_code.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    qr_code_filename = f"cancel_qr_{order.id}_{timestamp}_{filename}"

                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], qr_code_filename)
                    cancel_qr_code.save(upload_path)

            if order.can_cancel_directly:
                # 待确认状态可以直接取消
                order.status = 'cancelled'
                order.cancel_reason = cancel_reason
                order.cancelled_at = datetime.utcnow()
                order.cancelled_by = user.username if user else 'guest'
                if qr_code_filename:
                    order.cancel_qr_code = qr_code_filename

                db.session.commit()

                # 发送取消订单推送通知
                try:
                    pushdeer_service.send_order_notification(order, 'order_cancelled')
                except Exception as e:
                    print(f"取消订单推送通知失败: {e}")

                flash('订单已成功取消', 'success')
            else:
                # 已确认/已支付状态需要管理员审批
                order.status = 'cancel_pending'
                order.cancel_reason = cancel_reason
                order.cancelled_by = user.username if user else 'guest'
                if qr_code_filename:
                    order.cancel_qr_code = qr_code_filename

                db.session.commit()

                # 发送取消申请推送通知
                try:
                    pushdeer_service.send_order_notification(order, 'cancel_request')
                except Exception as e:
                    print(f"取消申请推送通知失败: {e}")

                flash('取消申请已提交，等待管理员审批', 'info')

            return redirect(url_for('main.order_detail', order_id=order_id))
        except Exception as e:
            db.session.rollback()
            flash('取消订单失败，请重试', 'error')
            # 检查是否使用Element UI样式
            return render_template('element_cancel_order.html', order=order, user=user)

    # 检查是否使用Element UI样式
    return render_template('element_cancel_order.html', order=order, user=user)

@bp.route('/api/drink_product/<int:product_id>')
def get_drink_product(product_id):
    """获取饮品产品详情API"""
    product = DrinkProduct.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'category': product.category,
        'image': product.image,
        'size_options': product.size_options,
        'temperature_options': product.temperature_options
    })

@bp.route('/test-wechat-qr')
def test_wechat_qr():
    """测试微信二维码长按识别功能"""
    return render_template('test_wechat_qr.html')

@bp.route('/test-qr-methods')
def test_qr_methods():
    """测试微信二维码长按识别 - 两种方案对比"""
    return render_template('test_qr_methods.html')

@bp.route('/order_history')
def order_history():
    """订单历史页面（重定向到我的订单）"""
    return redirect(url_for('main.my_orders'))
