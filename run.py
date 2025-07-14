#!/usr/bin/env python3
from app import create_app
import argparse

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行发财小狗饮品店应用')
    parser.add_argument('--host', default='127.0.0.1', help='主机地址')
    parser.add_argument('--port', type=int, default=5000, help='端口号')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    print(f"🚀 启动发财小狗饮品店应用...")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"🔧 调试模式: {'开启' if args.debug else '关闭'}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
