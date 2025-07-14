from app import create_app

app = create_app()

# 在应用上下文中导入模型
with app.app_context():
    from app.models import db, User, DrinkProduct, Order, OrderItem, Category

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'DrinkProduct': DrinkProduct, 'Order': Order, 'OrderItem': OrderItem, 'Category': Category}

def migrate_cancel_fields():
    """添加订单取消相关字段"""
    with app.app_context():
        from sqlalchemy import text

        try:
            # 使用原生SQL添加字段
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN cancel_reason TEXT'))
            db.session.commit()
            print("添加字段: cancel_reason")
        except Exception as e:
            print(f"cancel_reason字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN cancelled_at DATETIME'))
            db.session.commit()
            print("添加字段: cancelled_at")
        except Exception as e:
            print(f"cancelled_at字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN cancelled_by VARCHAR(80)'))
            db.session.commit()
            print("添加字段: cancelled_by")
        except Exception as e:
            print(f"cancelled_by字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN cancel_approved_by VARCHAR(80)'))
            db.session.commit()
            print("添加字段: cancel_approved_by")
        except Exception as e:
            print(f"cancel_approved_by字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN cancel_approved_at DATETIME'))
            db.session.commit()
            print("添加字段: cancel_approved_at")
        except Exception as e:
            print(f"cancel_approved_at字段可能已存在: {e}")
            db.session.rollback()

        print("数据库迁移完成！")

        # 添加退款相关字段
        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_qr_code VARCHAR(255)'))
            db.session.commit()
            print("添加字段: refund_qr_code")
        except Exception as e:
            print(f"refund_qr_code字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_status VARCHAR(20)'))
            db.session.commit()
            print("添加字段: refund_status")
        except Exception as e:
            print(f"refund_status字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_approved_by VARCHAR(80)'))
            db.session.commit()
            print("添加字段: refund_approved_by")
        except Exception as e:
            print(f"refund_approved_by字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_approved_at DATETIME'))
            db.session.commit()
            print("添加字段: refund_approved_at")
        except Exception as e:
            print(f"refund_approved_at字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_completed_at DATETIME'))
            db.session.commit()
            print("添加字段: refund_completed_at")
        except Exception as e:
            print(f"refund_completed_at字段可能已存在: {e}")
            db.session.rollback()

        try:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN refund_admin_notes TEXT'))
            db.session.commit()
            print("添加字段: refund_admin_notes")
        except Exception as e:
            print(f"refund_admin_notes字段可能已存在: {e}")
            db.session.rollback()

        print("退款字段迁移完成！")

def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 检查是否已有示例数据
        if Category.query.count() == 0:
            # 添加示例分类
            categories = [
                Category(name="咖啡", description="各种咖啡饮品", sort_order=1),
                Category(name="茶饮", description="茶类饮品", sort_order=2),
                Category(name="果汁", description="新鲜果汁饮品", sort_order=3),
                Category(name="特色饮品", description="特色创意饮品", sort_order=4),
                Category(name="其他", description="其他类型饮品", sort_order=5)
            ]

            for category in categories:
                db.session.add(category)
            db.session.commit()
            print("示例分类已添加")

        if DrinkProduct.query.count() == 0:
            # 添加示例饮品产品
            coffee_category = Category.query.filter_by(name="咖啡").first()
            tea_category = Category.query.filter_by(name="茶饮").first()
            juice_category = Category.query.filter_by(name="果汁").first()
            special_category = Category.query.filter_by(name="特色饮品").first()

            products = [
                DrinkProduct(
                    name="美式咖啡",
                    description="经典美式咖啡，香浓醇厚",
                    price=25.0,
                    category_id=coffee_category.id if coffee_category else None,
                    category="咖啡",
                    image="uploads/coffee_americano.jpg",
                    size_options="small,medium,large",
                    temperature_options="hot,ice"
                ),
                DrinkProduct(
                    name="拿铁咖啡",
                    description="香滑拿铁，奶香浓郁",
                    price=32.0,
                    category_id=coffee_category.id if coffee_category else None,
                    category="咖啡",
                    image="uploads/coffee_latte.jpg",
                    size_options="small,medium,large",
                    temperature_options="hot,ice"
                ),
                DrinkProduct(
                    name="柠檬蜂蜜茶",
                    description="清香柠檬配蜂蜜，酸甜可口",
                    price=28.0,
                    category_id=tea_category.id if tea_category else None,
                    category="茶饮",
                    image="uploads/tea_lemon_honey.jpg",
                    size_options="medium,large",
                    temperature_options="hot,normal,ice"
                ),
                DrinkProduct(
                    name="鲜榨橙汁",
                    description="新鲜橙子现榨，维C丰富",
                    price=22.0,
                    category_id=juice_category.id if juice_category else None,
                    category="果汁",
                    image="uploads/juice_orange.jpg",
                    size_options="medium,large",
                    temperature_options="normal,ice"
                ),
                DrinkProduct(
                    name="抹茶拿铁",
                    description="日式抹茶与牛奶的完美结合",
                    price=35.0,  
                    category_id=special_category.id if special_category else None,
                    category="特色饮品",
                    image="uploads/matcha_latte.jpg",
                    size_options="small,medium,large",
                    temperature_options="hot,ice"
                )
            ]
            
            for product in products:
                db.session.add(product)
            
            db.session.commit()
            print("示例数据已添加")

if __name__ == '__main__':
    init_db()

    # 启动WebSocket打印服务器
    try:
        from app.websocket.print_server import start_print_server_thread
        print("正在启动WebSocket打印服务器...")
        start_print_server_thread()
        print("WebSocket打印服务器已启动在端口 8765")
    except Exception as e:
        print(f"启动WebSocket打印服务器失败: {e}")

    # 启动Flask应用
    print("正在启动Flask应用...")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
