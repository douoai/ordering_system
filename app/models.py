from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json

# 创建一个全局的db实例，这将在__init__.py中被初始化
db = SQLAlchemy()

class Category(db.Model):
    """饮品分类模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)  # 排序顺序
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Category {self.name}>'

class User(db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)  # 地址
    preferences = db.Column(db.Text, nullable=True)  # 偏好记录
    notes = db.Column(db.Text, nullable=True)  # 备注
    is_vip = db.Column(db.Boolean, default=False)  # VIP状态
    total_orders = db.Column(db.Integer, default=0)  # 总订单数
    total_spent = db.Column(db.Float, default=0.0)  # 总消费金额
    last_order_at = db.Column(db.DateTime, nullable=True)  # 最后下单时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联订单
    orders = db.relationship('Order', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def update_order_stats(self):
        """更新用户订单统计"""
        confirmed_orders = Order.query.filter_by(user_id=self.id, status='confirmed').all()
        self.total_orders = len(confirmed_orders)
        self.total_spent = sum(order.total_amount for order in confirmed_orders)
        if confirmed_orders:
            self.last_order_at = max(order.created_at for order in confirmed_orders)

        # 根据消费金额判断VIP状态
        self.is_vip = self.total_spent >= 500.0  # 消费满500元成为VIP

class DrinkProduct(db.Model):
    """饮品产品模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, nullable=True)  # 简化：不使用外键
    category = db.Column(db.String(50), nullable=True)  # 保留原有字段作为备用
    image = db.Column(db.String(200), nullable=True)  # 产品图片
    size_options = db.Column(db.String(200), nullable=True)  # 规格选项（小杯、中杯、大杯）
    temperature_options = db.Column(db.String(100), nullable=True)  # 温度选项（热、冰、常温）
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联订单项
    order_items = db.relationship('OrderItem', backref='drink_product', lazy=True)

    @property
    def category_name(self):
        """获取分类名称"""
        if self.category_id:
            category = Category.query.get(self.category_id)
            if category:
                return category.name
        return self.category or '未分类'

    def __repr__(self):
        return f'<DrinkProduct {self.name}>'

class Order(db.Model):
    """订单模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, rejected, completed, refunded, cancelled, cancel_pending
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by = db.Column(db.String(80), nullable=True)  # 管理员用户名
    refund_reason = db.Column(db.Text, nullable=True)  # 退款原因
    refunded_at = db.Column(db.DateTime, nullable=True)  # 退款时间
    refund_qr_code = db.Column(db.String(255), nullable=True)  # 退款收款二维码路径
    refund_status = db.Column(db.String(20), nullable=True)  # 退款状态: pending, approved, rejected, completed
    refund_approved_by = db.Column(db.String(80), nullable=True)  # 退款审批人
    refund_approved_at = db.Column(db.DateTime, nullable=True)  # 退款审批时间
    refund_completed_at = db.Column(db.DateTime, nullable=True)  # 退款完成时间
    refund_admin_notes = db.Column(db.Text, nullable=True)  # 管理员退款备注

    # 取消订单相关字段
    cancel_reason = db.Column(db.Text, nullable=True)  # 取消原因
    cancelled_at = db.Column(db.DateTime, nullable=True)  # 取消时间
    cancelled_by = db.Column(db.String(80), nullable=True)  # 取消操作者（用户或管理员）
    cancel_approved_by = db.Column(db.String(80), nullable=True)  # 取消审批者（管理员）
    cancel_approved_at = db.Column(db.DateTime, nullable=True)  # 取消审批时间
    cancel_qr_code = db.Column(db.String(255), nullable=True)  # 取消订单时的收款二维码路径（已付款订单需要）
    
    # 关联订单项
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id}>'
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.order_items)

    @property
    def can_refund(self):
        """判断是否可以退款"""
        # 待确认状态可以直接退款
        if self.status == 'pending':
            return True
        # 已支付状态可以申请退款（需要上传二维码）
        elif self.status in ['paid', 'confirmed']:
            return True
        return False

    @property
    def can_refund_directly(self):
        """判断是否可以直接退款（无需审批）"""
        return self.status == 'pending'

    @property
    def needs_refund_approval(self):
        """判断退款是否需要管理员审批"""
        return self.status in ['paid', 'confirmed']

    @property
    def refund_status_display(self):
        """退款状态显示"""
        if not self.refund_status:
            return None
        status_map = {
            'pending': '退款审核中',
            'approved': '退款已批准',
            'rejected': '退款已拒绝',
            'completed': '退款已完成'
        }
        return status_map.get(self.refund_status, self.refund_status)

    @property
    def can_cancel(self):
        """判断是否可以取消订单"""
        # 待确认状态可以直接取消
        if self.status == 'pending':
            return True
        # 已确认状态需要管理员审批
        elif self.status == 'confirmed':
            return True
        # 其他状态不能取消
        return False

    @property
    def can_cancel_directly(self):
        """判断是否可以直接取消（无需审批）"""
        return self.status == 'pending'

    @property
    def needs_cancel_approval(self):
        """判断取消是否需要管理员审批"""
        return self.status == 'confirmed' and self.status != 'cancel_pending'

    @property
    def needs_cancel_qr_code(self):
        """判断取消订单是否需要上传收款二维码（已确认订单需要）"""
        return self.status == 'confirmed'

    @property
    def is_cancelled(self):
        """判断订单是否已取消"""
        return self.status == 'cancelled'

    @property
    def is_cancel_pending(self):
        """判断订单是否等待取消审批"""
        return self.status == 'cancel_pending'

    @property
    def status_display(self):
        """状态显示名称"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'paid': '已支付',
            'rejected': '已拒绝',
            'completed': '已完成',
            'refunded': '已退款',
            'cancelled': '已取消',
            'cancel_pending': '取消待审批'
        }
        return status_map.get(self.status, self.status)

class OrderItem(db.Model):
    """订单项模型"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    drink_product_id = db.Column(db.Integer, db.ForeignKey('drink_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(20), nullable=True)  # 规格选择
    temperature = db.Column(db.String(20), nullable=True)  # 温度选择
    sugar_level = db.Column(db.String(20), nullable=True)  # 糖度选择
    ice_level = db.Column(db.String(20), nullable=True)  # 冰量选择
    notes = db.Column(db.Text, nullable=True)  # 特殊要求

    def __repr__(self):
        return f'<OrderItem {self.id}>'


class PushDeerConfig(db.Model):
    """PushDeer推送配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 配置名称
    pushkey = db.Column(db.String(200), nullable=False)  # PushDeer推送密钥
    endpoint = db.Column(db.String(200), nullable=True, default='https://api2.pushdeer.com')  # API端点
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    description = db.Column(db.Text, nullable=True)  # 配置描述
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 事件配置字段 - 使用JSON存储
    events_config = db.Column(db.Text, nullable=True)  # JSON格式存储事件配置

    def get_events_config(self):
        """获取事件配置"""
        import json

        # 默认配置
        default_config = {
            'new_order': True,
            'order_confirmed': True,
            'order_completed': True,
            'order_cancelled': True,
            'order_refunded': True,
        }

        # 如果有保存的配置，则使用保存的配置
        if self.events_config:
            try:
                saved_config = json.loads(self.events_config)
                # 合并默认配置和保存的配置
                default_config.update(saved_config)
            except (json.JSONDecodeError, TypeError):
                pass  # 如果解析失败，使用默认配置

        # 返回格式化的配置
        return {
            'new_order': {
                'enabled': default_config.get('new_order', True),
                'name': '新订单通知',
                'description': '用户下单时发送通知'
            },
            'order_confirmed': {
                'enabled': default_config.get('order_confirmed', True),
                'name': '订单确认通知',
                'description': '管理员确认订单时发送通知'
            },
            'order_completed': {
                'enabled': default_config.get('order_completed', True),
                'name': '订单完成通知',
                'description': '订单制作完成时发送通知'
            },
            'order_cancelled': {
                'enabled': default_config.get('order_cancelled', True),
                'name': '订单取消通知',
                'description': '订单被取消时发送通知'
            },
            'order_refunded': {
                'enabled': default_config.get('order_refunded', True),
                'name': '退款通知',
                'description': '退款处理时发送通知'
            }
        }

    def set_events_config(self, events_config):
        """设置事件配置"""
        import json
        try:
            # 将配置保存为JSON字符串
            self.events_config = json.dumps(events_config)
        except (TypeError, ValueError) as e:
            print(f"保存事件配置失败: {e}")

    def is_event_enabled(self, event_type):
        """检查特定事件是否启用"""
        events = self.get_events_config()
        return events.get(event_type, {}).get('enabled', True)

    def __repr__(self):
        return f'<PushDeerConfig {self.name}>'


class PrinterConfig(db.Model):
    """打印机配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 打印机名称
    ip_address = db.Column(db.String(45), nullable=True)  # 打印机IP地址
    port = db.Column(db.Integer, nullable=True, default=9100)  # 打印机端口
    printer_type = db.Column(db.String(50), nullable=False, default='thermal')  # 打印机类型: thermal, laser, inkjet
    paper_width = db.Column(db.Integer, nullable=False, default=80)  # 纸张宽度(mm)
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    auto_print_orders = db.Column(db.Boolean, default=True)  # 是否自动打印订单
    print_copies = db.Column(db.Integer, default=1)  # 打印份数
    description = db.Column(db.Text, nullable=True)  # 描述
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PrinterConfig {self.name}>'


class PrintJob(db.Model):
    """打印任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)  # 关联订单
    printer_id = db.Column(db.Integer, db.ForeignKey('printer_config.id'), nullable=True)  # 关联打印机
    job_type = db.Column(db.String(50), nullable=False, default='order')  # 任务类型: order, receipt, label
    status = db.Column(db.String(20), default='pending')  # 状态: pending, printing, completed, failed, cancelled
    print_content = db.Column(db.Text, nullable=True)  # 打印内容
    print_data = db.Column(db.Text, nullable=True)  # 打印数据(JSON格式)
    copies = db.Column(db.Integer, default=1)  # 打印份数
    priority = db.Column(db.Integer, default=5)  # 优先级(1-10, 数字越小优先级越高)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    started_at = db.Column(db.DateTime, nullable=True)  # 开始打印时间
    completed_at = db.Column(db.DateTime, nullable=True)  # 完成时间
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    retry_count = db.Column(db.Integer, default=0)  # 重试次数
    max_retries = db.Column(db.Integer, default=3)  # 最大重试次数

    # 关联关系
    order = db.relationship('Order', backref='print_jobs')
    printer = db.relationship('PrinterConfig', backref='print_jobs')

    def __repr__(self):
        return f'<PrintJob {self.id} - {self.job_type}>'

    @property
    def status_display(self):
        """状态显示名称"""
        status_map = {
            'pending': '等待打印',
            'printing': '正在打印',
            'completed': '打印完成',
            'failed': '打印失败',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def can_retry(self):
        """是否可以重试"""
        return self.status == 'failed' and self.retry_count < self.max_retries

    def mark_as_printing(self):
        """标记为正在打印"""
        self.status = 'printing'
        self.started_at = datetime.utcnow()

    def mark_as_completed(self):
        """标记为打印完成"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()

    def mark_as_failed(self, error_message=None):
        """标记为打印失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 推送事件配置（JSON格式存储）
    events_config = db.Column(db.Text, nullable=True, default='{}')  # 事件配置

    def get_events_config(self):
        """获取事件配置"""
        try:
            return json.loads(self.events_config or '{}')
        except:
            return {}

    def set_events_config(self, config_dict):
        """设置事件配置"""
        self.events_config = json.dumps(config_dict)

    def __repr__(self):
        return f'<PushDeerConfig {self.name}>'


class PushRecord(db.Model):
    """推送记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('push_deer_config.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)  # 关联订单（可选）
    event_type = db.Column(db.String(50), nullable=False)  # 事件类型
    title = db.Column(db.String(200), nullable=False)  # 推送标题
    content = db.Column(db.Text, nullable=False)  # 推送内容
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, success, failed
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    response_data = db.Column(db.Text, nullable=True)  # 响应数据（JSON格式）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)  # 实际发送时间

    # 关联配置和订单
    config = db.relationship('PushDeerConfig', backref='push_records')
    order = db.relationship('Order', backref='push_records')

    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            'pending': '待发送',
            'success': '发送成功',
            'failed': '发送失败'
        }
        return status_map.get(self.status, self.status)

    @property
    def event_type_text(self):
        """事件类型文本"""
        event_map = {
            'new_order': '新订单',
            'order_confirmed': '订单确认',
            'order_cancelled': '订单取消',
            'order_refunded': '订单退款',
            'test': '测试推送'
        }
        return event_map.get(self.event_type, self.event_type)

    def get_response_data(self):
        """获取响应数据"""
        try:
            return json.loads(self.response_data or '{}')
        except:
            return {}

    def set_response_data(self, data_dict):
        """设置响应数据"""
        self.response_data = json.dumps(data_dict)

    def __repr__(self):
        return f'<PushRecord {self.id}>'


class Announcement(db.Model):
    """首页公告模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # 公告标题
    content = db.Column(db.Text, nullable=False)  # 公告内容
    announcement_type = db.Column(db.String(50), nullable=False, default='info')  # 公告类型
    priority = db.Column(db.Integer, default=0)  # 优先级，数字越大优先级越高
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    show_on_homepage = db.Column(db.Boolean, default=True)  # 是否在首页显示
    start_time = db.Column(db.DateTime, nullable=True)  # 开始显示时间
    end_time = db.Column(db.DateTime, nullable=True)  # 结束显示时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 创建者

    # 关联创建者
    creator = db.relationship('User', backref='announcements')

    @property
    def type_display(self):
        """获取公告类型显示名称"""
        type_map = {
            'info': '信息',
            'warning': '警告',
            'success': '成功',
            'danger': '重要',
            'primary': '主要',
            'secondary': '次要'
        }
        return type_map.get(self.announcement_type, self.announcement_type)

    @property
    def is_valid(self):
        """检查公告是否在有效期内"""
        now = datetime.utcnow()

        # 检查开始时间
        if self.start_time and now < self.start_time:
            return False

        # 检查结束时间
        if self.end_time and now > self.end_time:
            return False

        return True

    @property
    def status_display(self):
        """获取状态显示"""
        if not self.is_active:
            return '已禁用'
        elif not self.is_valid:
            return '已过期'
        else:
            return '正常'

    def __repr__(self):
        return f'<Announcement {self.id}: {self.title}>'

class MenuConfig(db.Model):
    """菜单配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    menu_key = db.Column(db.String(50), unique=True, nullable=False)  # 菜单唯一标识
    menu_name = db.Column(db.String(100), nullable=False)  # 菜单显示名称
    menu_icon = db.Column(db.String(50), nullable=False)  # 菜单图标
    menu_url = db.Column(db.String(200), nullable=True)  # 菜单链接
    parent_key = db.Column(db.String(50), nullable=True)  # 父菜单标识
    sort_order = db.Column(db.Integer, default=0)  # 排序顺序
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    is_visible = db.Column(db.Boolean, default=True)  # 是否显示
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MenuConfig {self.menu_name}>'

    @classmethod
    def get_menu_tree(cls):
        """获取菜单树结构"""
        # 获取所有启用且可见的菜单，按排序顺序
        menus = cls.query.filter_by(is_active=True, is_visible=True).order_by(cls.sort_order).all()

        # 构建菜单树
        menu_tree = []
        menu_dict = {}

        # 先处理所有菜单项
        for menu in menus:
            menu_dict[menu.menu_key] = {
                'key': menu.menu_key,
                'name': menu.menu_name,
                'icon': menu.menu_icon,
                'url': menu.menu_url,
                'parent_key': menu.parent_key,
                'sort_order': menu.sort_order,
                'children': []
            }

        # 构建树结构
        for menu in menus:
            if menu.parent_key and menu.parent_key in menu_dict:
                # 有父菜单，添加到父菜单的children中
                menu_dict[menu.parent_key]['children'].append(menu_dict[menu.menu_key])
            else:
                # 顶级菜单
                menu_tree.append(menu_dict[menu.menu_key])

        return menu_tree

class AdminUser(db.Model):
    """管理员用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(100), nullable=True)  # 真实姓名
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_super_admin = db.Column(db.Boolean, default=False)  # 超级管理员
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联权限
    roles = db.relationship('AdminRole', secondary='admin_user_roles', back_populates='users')

    def __repr__(self):
        return f'<AdminUser {self.username}>'

    def set_password(self, password):
        """设置密码"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_code):
        """检查是否有指定权限"""
        if self.is_super_admin:
            return True

        for role in self.roles:
            if role.is_active:
                for permission in role.permissions:
                    if permission.is_active and permission.permission_code == permission_code:
                        return True
        return False

    def get_permissions(self):
        """获取用户所有权限"""
        if self.is_super_admin:
            return Permission.query.filter_by(is_active=True).all()

        permissions = set()
        for role in self.roles:
            if role.is_active:
                for permission in role.permissions:
                    if permission.is_active:
                        permissions.add(permission)
        return list(permissions)

class AdminRole(db.Model):
    """管理员角色模型"""
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), unique=True, nullable=False)
    role_code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联用户和权限
    users = db.relationship('AdminUser', secondary='admin_user_roles', back_populates='roles')
    permissions = db.relationship('Permission', secondary='role_permissions', back_populates='roles')

    def __repr__(self):
        return f'<AdminRole {self.role_name}>'

class Permission(db.Model):
    """权限模型"""
    id = db.Column(db.Integer, primary_key=True)
    permission_name = db.Column(db.String(100), nullable=False)
    permission_code = db.Column(db.String(50), unique=True, nullable=False)
    module = db.Column(db.String(50), nullable=False)  # 所属模块
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联角色
    roles = db.relationship('AdminRole', secondary='role_permissions', back_populates='permissions')

    def __repr__(self):
        return f'<Permission {self.permission_name}>'

# 关联表
admin_user_roles = db.Table('admin_user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('admin_user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id'), primary_key=True)
)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

class PaymentConfig(db.Model):
    """支付配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    payment_type = db.Column(db.String(20), nullable=False)  # alipay, wechat
    payment_name = db.Column(db.String(50), nullable=False)  # 支付方式名称
    qr_code_path = db.Column(db.String(200), nullable=True)  # 二维码图片路径
    qr_code_url = db.Column(db.Text, nullable=True)  # 二维码URL（如果是在线图片）
    account_name = db.Column(db.String(100), nullable=True)  # 收款账户名
    account_info = db.Column(db.Text, nullable=True)  # 账户信息
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    sort_order = db.Column(db.Integer, default=0)  # 排序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentConfig {self.payment_name}>'

    @classmethod
    def get_active_payments(cls):
        """获取启用的支付方式"""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order).all()

    @property
    def qr_code_image_url(self):
        """获取二维码图片URL"""
        if self.qr_code_url:
            return self.qr_code_url
        elif self.qr_code_path:
            from flask import url_for
            return url_for('static', filename=self.qr_code_path)
        else:
            from flask import url_for
            return url_for('static', filename='images/placeholder_qr.svg')
