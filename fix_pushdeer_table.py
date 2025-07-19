#!/usr/bin/env python3
"""
修复PushDeer配置表，添加缺失的字段
"""

import sqlite3
import os

def fix_pushdeer_table():
    """修复PushDeer配置表"""
    db_path = 'instance/audio_order_system.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查现有字段
        cursor.execute("PRAGMA table_info(push_deer_config)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"现有字段: {columns}")
        
        # 需要添加的字段
        new_columns = [
            ('enable_order_created', 'BOOLEAN DEFAULT 1'),
            ('enable_order_confirmed', 'BOOLEAN DEFAULT 1'),
            ('enable_order_completed', 'BOOLEAN DEFAULT 1'),
            ('enable_order_cancelled', 'BOOLEAN DEFAULT 1'),
            ('enable_refund_requested', 'BOOLEAN DEFAULT 1'),
            ('enable_refund_approved', 'BOOLEAN DEFAULT 1')
        ]
        
        # 添加缺失的字段
        for column_name, column_def in new_columns:
            if column_name not in columns:
                try:
                    sql = f"ALTER TABLE push_deer_config ADD COLUMN {column_name} {column_def}"
                    cursor.execute(sql)
                    print(f"✅ 已添加字段: {column_name}")
                except Exception as e:
                    print(f"❌ 添加字段 {column_name} 失败: {e}")
        
        # 提交更改
        conn.commit()
        print("✅ 数据库修复完成")
        
        # 验证修复结果
        cursor.execute("PRAGMA table_info(push_deer_config)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"修复后字段: {updated_columns}")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    print("🔧 开始修复PushDeer配置表...")
    fix_pushdeer_table()
    print("🎉 修复完成！")
