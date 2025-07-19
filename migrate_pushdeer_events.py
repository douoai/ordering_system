#!/usr/bin/env python3
"""
添加PushDeer事件配置字段的数据库迁移
"""

from app import create_app, db
from app.models import PushDeerConfig

def migrate_pushdeer_events():
    """添加PushDeer事件配置字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查是否需要添加新字段
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('push_deer_config')]
            
            new_columns = [
                'enable_order_created',
                'enable_order_confirmed', 
                'enable_order_completed',
                'enable_order_cancelled',
                'enable_refund_requested',
                'enable_refund_approved'
            ]
            
            missing_columns = [col for col in new_columns if col not in columns]
            
            if missing_columns:
                print(f"需要添加的字段: {missing_columns}")
                
                # 添加新字段
                for column in missing_columns:
                    try:
                        db.engine.execute(f'ALTER TABLE push_deer_config ADD COLUMN {column} BOOLEAN DEFAULT 1')
                        print(f"✅ 已添加字段: {column}")
                    except Exception as e:
                        print(f"❌ 添加字段 {column} 失败: {e}")
                
                # 更新现有记录的默认值
                try:
                    configs = PushDeerConfig.query.all()
                    for config in configs:
                        config.enable_order_created = True
                        config.enable_order_confirmed = True
                        config.enable_order_completed = True
                        config.enable_order_cancelled = True
                        config.enable_refund_requested = True
                        config.enable_refund_approved = True
                    
                    db.session.commit()
                    print(f"✅ 已更新 {len(configs)} 个配置的默认值")
                    
                except Exception as e:
                    print(f"❌ 更新默认值失败: {e}")
                    db.session.rollback()
            else:
                print("✅ 所有字段已存在，无需迁移")
                
        except Exception as e:
            print(f"❌ 迁移失败: {e}")

if __name__ == '__main__':
    print("🔄 开始PushDeer事件配置字段迁移...")
    migrate_pushdeer_events()
    print("🎉 迁移完成！")
