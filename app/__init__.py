from flask import Flask
from config import Config
import secrets

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(Config)

    # 导入并初始化数据库
    from app.models import db
    db.init_app(app)

    # 注册蓝图
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # 注册打印管理蓝图
    from app.admin.print_routes import bp as print_bp
    app.register_blueprint(print_bp)

    # 注册模板函数
    @app.template_global()
    def get_admin_menu_items():
        """获取管理后台菜单项"""
        from app.models import MenuConfig
        try:
            menus = MenuConfig.query.filter_by(is_active=True, is_visible=True).order_by(MenuConfig.sort_order).all()
            return menus
        except:
            # 如果数据库还没有菜单配置表，返回默认菜单
            return []

    @app.template_global()
    def csrf_token():
        """生成CSRF token"""
        return secrets.token_hex(16)

    return app
