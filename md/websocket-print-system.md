# 🖨️ WebSocket打印管理系统

## 🎯 系统概述

WebSocket打印管理系统是发财小狗饮品店的核心功能之一，实现了订单确认后自动推送到外部打印设备的功能。系统采用WebSocket协议，确保实时、可靠的打印任务传输。

## 🏗️ 系统架构

### 核心组件
- **WebSocket服务器** - 端口8765，处理客户端连接
- **打印服务** - 生成小票内容，管理打印任务
- **管理后台** - 打印机配置，任务监控
- **数据库模型** - 打印机配置，打印任务记录

### 技术栈
- **后端**: Python + Flask + WebSockets
- **前端**: HTML5 + JavaScript + Element UI
- **数据库**: SQLite
- **协议**: WebSocket (RFC 6455)

## 🔧 功能特性

### 自动打印流程
1. **订单确认触发** - 管理员确认订单时自动创建打印任务
2. **内容生成** - 自动生成格式化的订单小票
3. **WebSocket推送** - 实时推送到所有连接的打印客户端
4. **状态跟踪** - 完整的打印任务生命周期管理

### 打印机管理
- **多设备支持** - 支持同时连接多台打印机
- **配置管理** - 打印机IP、端口、类型等配置
- **状态监控** - 实时监控打印机在线状态
- **自动重试** - 打印失败时自动重试机制

## 📡 WebSocket协议

### 服务器地址
```
ws://localhost:8765
```

### 消息格式

#### 1. 欢迎消息 (服务器 → 客户端)
```json
{
  "type": "welcome",
  "message": "欢迎连接到发财小狗饮品店打印服务",
  "timestamp": "2025-07-14T10:30:00",
  "server_info": {
    "name": "发财小狗饮品店打印服务器",
    "version": "1.0.0",
    "capabilities": ["order_print", "receipt_print", "status_update"]
  }
}
```

#### 2. 新订单推送 (服务器 → 客户端)
```json
{
  "type": "new_order",
  "timestamp": "2025-07-14T10:30:00",
  "order": {
    "job_id": 123,
    "order_id": 456,
    "type": "order_receipt",
    "content": "================================\n        发财小狗饮品店\n================================\n订单号: #456\n时间: 2025-07-14 10:30:00\n状态: 已确认\n--------------------------------\n珍珠奶茶\n  规格: 大杯 | 温度: 正常冰 | 糖度: 正常糖\n  1 x ¥25.00 = ¥25.00\n--------------------------------\n总计: ¥25.00\n================================\n      谢谢惠顾，欢迎再来！\n================================\n",
    "copies": 1,
    "priority": 1,
    "order_info": {
      "id": 456,
      "status": "confirmed",
      "total_amount": 25.00,
      "customer_phone": "13800138000"
    },
    "printer_config": {
      "paper_width": 80,
      "printer_type": "thermal"
    }
  }
}
```

#### 3. 打印状态反馈 (客户端 → 服务器)
```json
{
  "type": "print_status",
  "timestamp": "2025-07-14T10:30:00",
  "job_id": 123,
  "status": "completed",
  "message": "打印成功"
}
```

#### 4. 心跳检测
```json
// Ping (双向)
{
  "type": "ping",
  "timestamp": "2025-07-14T10:30:00"
}

// Pong (响应)
{
  "type": "pong",
  "timestamp": "2025-07-14T10:30:00"
}
```

## 🗄️ 数据库模型

### PrinterConfig (打印机配置)
```sql
CREATE TABLE printer_config (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- 打印机名称
    ip_address VARCHAR(45),               -- IP地址
    port INTEGER DEFAULT 9100,            -- 端口
    printer_type VARCHAR(50) DEFAULT 'thermal', -- 类型
    paper_width INTEGER DEFAULT 80,       -- 纸张宽度(mm)
    is_active BOOLEAN DEFAULT 1,          -- 是否启用
    auto_print_orders BOOLEAN DEFAULT 1,  -- 自动打印订单
    print_copies INTEGER DEFAULT 1,       -- 打印份数
    description TEXT,                      -- 描述
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### PrintJob (打印任务)
```sql
CREATE TABLE print_job (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,            -- 关联订单
    printer_id INTEGER,                   -- 关联打印机
    job_type VARCHAR(50) DEFAULT 'order', -- 任务类型
    status VARCHAR(20) DEFAULT 'pending', -- 状态
    print_content TEXT,                   -- 打印内容
    copies INTEGER DEFAULT 1,             -- 打印份数
    priority INTEGER DEFAULT 5,           -- 优先级(1-10)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,                  -- 开始时间
    completed_at DATETIME,                -- 完成时间
    error_message TEXT,                   -- 错误信息
    retry_count INTEGER DEFAULT 0,        -- 重试次数
    max_retries INTEGER DEFAULT 3,        -- 最大重试次数
    FOREIGN KEY (order_id) REFERENCES "order" (id),
    FOREIGN KEY (printer_id) REFERENCES printer_config (id)
);
```

## 🎮 管理后台

### 访问地址
```
http://localhost:5000/admin/print/
```

### 功能模块

#### 1. 打印管理首页
- **统计信息** - 打印机数量、任务统计
- **服务器状态** - WebSocket服务器运行状态
- **连接监控** - 实时显示连接的客户端
- **快速操作** - 测试打印、添加打印机等

#### 2. 打印机管理
- **添加打印机** - 配置新的打印设备
- **编辑配置** - 修改打印机参数
- **启用/禁用** - 控制打印机状态
- **测试打印** - 发送测试打印命令

#### 3. 打印任务管理
- **任务列表** - 查看所有打印任务
- **状态筛选** - 按状态筛选任务
- **重试失败** - 重新执行失败的任务
- **取消任务** - 取消待处理的任务

## 🔌 客户端集成

### JavaScript客户端示例
```javascript
// 连接WebSocket服务器
const ws = new WebSocket('ws://localhost:8765');

// 连接成功
ws.onopen = function(event) {
    console.log('连接到打印服务器');
    
    // 发送打印机信息
    ws.send(JSON.stringify({
        type: 'printer_info',
        timestamp: new Date().toISOString(),
        printer: {
            name: '收银台打印机',
            model: 'TP-80',
            status: 'ready'
        }
    }));
};

// 接收消息
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'welcome':
            console.log('收到欢迎消息:', data.message);
            break;
            
        case 'new_order':
            // 处理新订单打印
            printOrder(data.order);
            break;
            
        case 'print_command':
            // 处理打印命令
            executePrintCommand(data.data);
            break;
    }
};

// 打印订单
function printOrder(order) {
    console.log('打印订单:', order.order_id);
    console.log('打印内容:', order.content);
    
    // 发送到实际打印机
    // ... 打印机驱动代码 ...
    
    // 发送打印状态
    ws.send(JSON.stringify({
        type: 'print_status',
        timestamp: new Date().toISOString(),
        job_id: order.job_id,
        status: 'completed',
        message: '打印成功'
    }));
}
```

### Python客户端示例
```python
import asyncio
import websockets
import json
from datetime import datetime

async def print_client():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # 发送打印机信息
        printer_info = {
            "type": "printer_info",
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "name": "厨房打印机",
                "model": "TM-T88V",
                "status": "ready"
            }
        }
        await websocket.send(json.dumps(printer_info))
        
        # 监听消息
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'new_order':
                # 处理新订单
                await handle_print_order(data['order'])
            elif data['type'] == 'ping':
                # 响应心跳
                pong = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(pong))

async def handle_print_order(order):
    print(f"打印订单 #{order['order_id']}")
    print(order['content'])
    
    # 模拟打印过程
    await asyncio.sleep(2)
    
    # 这里添加实际的打印机驱动代码
    # ...

# 运行客户端
asyncio.run(print_client())
```

## 🚀 部署和配置

### 启动服务器
```bash
# 启动Flask应用（包含WebSocket服务器）
python app.py
```

### 配置打印机
1. 访问管理后台: http://localhost:5000/admin/print/
2. 点击"添加打印机"
3. 填写打印机信息:
   - 名称: 收银台打印机
   - IP地址: 192.168.1.100
   - 端口: 9100
   - 类型: thermal
   - 纸张宽度: 80mm

### 测试连接
1. 启动客户端程序
2. 在管理后台查看连接状态
3. 点击"测试打印"验证功能

## ⚠️ 注意事项

### 网络配置
- 确保端口8765未被占用
- 防火墙允许WebSocket连接
- 客户端能访问服务器IP

### 安全考虑
- 生产环境建议使用WSS (WebSocket Secure)
- 添加客户端认证机制
- 限制连接来源IP

### 性能优化
- 合理设置心跳间隔
- 控制并发连接数
- 优化打印内容大小

## 📞 技术支持

### 常见问题
1. **连接失败** - 检查服务器是否启动，端口是否开放
2. **打印失败** - 检查打印机配置，网络连接
3. **消息丢失** - 检查WebSocket连接稳定性

### 调试工具
- WebSocket连接测试工具
- 打印服务器状态监控
- 详细的日志记录

---

*让打印管理变得智能高效！*
