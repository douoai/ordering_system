# 🖨️ 发财小狗饮品店 - 打印系统对接指南

## 📋 系统概述

发财小狗饮品店的打印系统采用WebSocket协议，支持与第三方打印软件进行实时对接。当管理员确认订单并选择"启用自动打印"时，系统会通过WebSocket推送订单信息到指定的客户端程序。

## 🔌 连接参数

### WebSocket服务器信息
```
协议: WebSocket (ws://)
地址: localhost (或服务器IP)
端口: 8765
路径: /
完整地址: ws://localhost:8765
```

### 连接要求
- 支持WebSocket协议 (RFC 6455)
- 支持JSON消息格式
- 支持UTF-8编码
- 建议启用心跳检测

## 📡 消息协议

### 1. 连接建立

客户端连接成功后，服务器会发送欢迎消息：

```json
{
  "type": "welcome",
  "message": "欢迎连接到发财小狗饮品店打印服务",
  "timestamp": "2025-07-14T10:30:00.000Z",
  "server_info": {
    "name": "发财小狗饮品店打印服务器",
    "version": "1.0.0",
    "capabilities": ["order_print", "receipt_print", "status_update"]
  }
}
```

### 2. 客户端注册

连接后，客户端应发送打印机信息：

```json
{
  "type": "printer_info",
  "timestamp": "2025-07-14T10:30:00.000Z",
  "printer": {
    "name": "收银台打印机",
    "model": "TP-80",
    "paper_width": 80,
    "capabilities": ["text", "qr_code", "barcode"],
    "status": "ready",
    "ip_address": "192.168.1.100"
  }
}
```

### 3. 订单打印任务

当管理员确认订单并启用自动打印时，服务器会推送：

```json
{
  "type": "new_order",
  "timestamp": "2025-07-14T10:30:00.000Z",
  "order": {
    "job_id": 123,
    "order_id": 456,
    "type": "order_receipt",
    "content": "================================\n        发财小狗饮品店\n================================\n订单号: #456\n时间: 2025-07-14 10:30:00\n状态: 已确认\n--------------------------------\n珍珠奶茶\n  规格: 大杯 | 温度: 正常冰 | 糖度: 正常糖\n  1 x ¥25.00 = ¥25.00\n--------------------------------\n总计: ¥25.00\n================================\n      谢谢惠顾，欢迎再来！\n================================\n",
    "copies": 1,
    "priority": 1,
    "target_printer": {
      "id": 1,
      "name": "收银台打印机",
      "ip_address": "192.168.1.100"
    },
    "order_info": {
      "id": 456,
      "status": "confirmed",
      "total_amount": 25.00,
      "created_at": "2025-07-14T10:30:00.000Z",
      "customer_phone": "13800138000"
    },
    "printer_config": {
      "paper_width": 80,
      "printer_type": "thermal"
    }
  }
}
```

### 4. 打印状态反馈

客户端处理完打印任务后，应发送状态反馈：

```json
{
  "type": "print_status",
  "timestamp": "2025-07-14T10:30:00.000Z",
  "job_id": 123,
  "status": "completed",
  "message": "打印成功"
}
```

状态值说明：
- `printing` - 正在打印
- `completed` - 打印完成
- `failed` - 打印失败

### 5. 心跳检测

服务器会定期发送ping消息，客户端应响应pong：

```json
// 服务器发送
{
  "type": "ping",
  "timestamp": "2025-07-14T10:30:00.000Z"
}

// 客户端响应
{
  "type": "pong",
  "timestamp": "2025-07-14T10:30:00.000Z"
}
```

## 💻 客户端实现示例

### JavaScript实现

```javascript
class PrintClient {
    constructor(serverUrl = 'ws://localhost:8765') {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.printerName = '我的打印机';
    }
    
    connect() {
        this.ws = new WebSocket(this.serverUrl);
        
        this.ws.onopen = () => {
            console.log('连接到打印服务器');
            this.sendPrinterInfo();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('连接已断开');
            // 可以实现重连逻辑
        };
        
        this.ws.onerror = (error) => {
            console.error('连接错误:', error);
        };
    }
    
    sendPrinterInfo() {
        const printerInfo = {
            type: 'printer_info',
            timestamp: new Date().toISOString(),
            printer: {
                name: this.printerName,
                model: 'JS Client v1.0',
                status: 'ready'
            }
        };
        this.ws.send(JSON.stringify(printerInfo));
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'welcome':
                console.log('收到欢迎消息:', data.message);
                break;
                
            case 'new_order':
                this.handlePrintOrder(data.order);
                break;
                
            case 'ping':
                this.sendPong();
                break;
        }
    }
    
    handlePrintOrder(order) {
        console.log('收到打印任务:', order.order_id);
        console.log('打印内容:', order.content);
        
        // 这里调用您的打印逻辑
        this.printContent(order.content);
        
        // 发送打印状态
        this.sendPrintStatus(order.job_id, 'completed', '打印成功');
    }
    
    printContent(content) {
        // 实现您的打印逻辑
        // 例如：调用打印机API、保存为文件等
        console.log('执行打印:', content);
    }
    
    sendPrintStatus(jobId, status, message) {
        const statusMsg = {
            type: 'print_status',
            timestamp: new Date().toISOString(),
            job_id: jobId,
            status: status,
            message: message
        };
        this.ws.send(JSON.stringify(statusMsg));
    }
    
    sendPong() {
        const pong = {
            type: 'pong',
            timestamp: new Date().toISOString()
        };
        this.ws.send(JSON.stringify(pong));
    }
}

// 使用示例
const client = new PrintClient();
client.connect();
```

### Python实现

```python
import asyncio
import websockets
import json
from datetime import datetime

class PrintClient:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.printer_name = '我的打印机'
    
    async def connect(self):
        async with websockets.connect(self.server_url) as websocket:
            await self.send_printer_info(websocket)
            
            async for message in websocket:
                data = json.loads(message)
                await self.handle_message(websocket, data)
    
    async def send_printer_info(self, websocket):
        printer_info = {
            "type": "printer_info",
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "name": self.printer_name,
                "model": "Python Client v1.0",
                "status": "ready"
            }
        }
        await websocket.send(json.dumps(printer_info))
    
    async def handle_message(self, websocket, data):
        if data['type'] == 'welcome':
            print(f"收到欢迎消息: {data['message']}")
        
        elif data['type'] == 'new_order':
            await self.handle_print_order(websocket, data['order'])
        
        elif data['type'] == 'ping':
            await self.send_pong(websocket)
    
    async def handle_print_order(self, websocket, order):
        print(f"收到打印任务: {order['order_id']}")
        print(f"打印内容: {order['content']}")
        
        # 这里调用您的打印逻辑
        success = self.print_content(order['content'])
        
        # 发送打印状态
        status = 'completed' if success else 'failed'
        message = '打印成功' if success else '打印失败'
        await self.send_print_status(websocket, order['job_id'], status, message)
    
    def print_content(self, content):
        # 实现您的打印逻辑
        print(f"执行打印: {content}")
        return True  # 返回打印是否成功
    
    async def send_print_status(self, websocket, job_id, status, message):
        status_msg = {
            "type": "print_status",
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "status": status,
            "message": message
        }
        await websocket.send(json.dumps(status_msg))
    
    async def send_pong(self, websocket):
        pong = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(pong))

# 使用示例
async def main():
    client = PrintClient()
    await client.connect()

asyncio.run(main())
```

### C# .NET实现

```csharp
using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

public class PrintClient
{
    private ClientWebSocket webSocket;
    private string serverUrl;
    private string printerName;
    
    public PrintClient(string serverUrl = "ws://localhost:8765")
    {
        this.serverUrl = serverUrl;
        this.printerName = "我的打印机";
        this.webSocket = new ClientWebSocket();
    }
    
    public async Task ConnectAsync()
    {
        await webSocket.ConnectAsync(new Uri(serverUrl), CancellationToken.None);
        await SendPrinterInfoAsync();
        await ListenForMessagesAsync();
    }
    
    private async Task SendPrinterInfoAsync()
    {
        var printerInfo = new
        {
            type = "printer_info",
            timestamp = DateTime.UtcNow.ToString("O"),
            printer = new
            {
                name = printerName,
                model = "C# Client v1.0",
                status = "ready"
            }
        };
        
        await SendMessageAsync(JsonSerializer.Serialize(printerInfo));
    }
    
    private async Task ListenForMessagesAsync()
    {
        var buffer = new byte[4096];
        
        while (webSocket.State == WebSocketState.Open)
        {
            var result = await webSocket.ReceiveAsync(
                new ArraySegment<byte>(buffer), 
                CancellationToken.None);
            
            if (result.MessageType == WebSocketMessageType.Text)
            {
                var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                await HandleMessageAsync(message);
            }
        }
    }
    
    private async Task HandleMessageAsync(string message)
    {
        var data = JsonSerializer.Deserialize<JsonElement>(message);
        var type = data.GetProperty("type").GetString();
        
        switch (type)
        {
            case "welcome":
                Console.WriteLine($"收到欢迎消息: {data.GetProperty("message").GetString()}");
                break;
                
            case "new_order":
                await HandlePrintOrderAsync(data.GetProperty("order"));
                break;
                
            case "ping":
                await SendPongAsync();
                break;
        }
    }
    
    private async Task HandlePrintOrderAsync(JsonElement order)
    {
        var orderId = order.GetProperty("order_id").GetInt32();
        var jobId = order.GetProperty("job_id").GetInt32();
        var content = order.GetProperty("content").GetString();
        
        Console.WriteLine($"收到打印任务: {orderId}");
        Console.WriteLine($"打印内容: {content}");
        
        // 这里调用您的打印逻辑
        bool success = PrintContent(content);
        
        // 发送打印状态
        string status = success ? "completed" : "failed";
        string statusMessage = success ? "打印成功" : "打印失败";
        await SendPrintStatusAsync(jobId, status, statusMessage);
    }
    
    private bool PrintContent(string content)
    {
        // 实现您的打印逻辑
        Console.WriteLine($"执行打印: {content}");
        return true; // 返回打印是否成功
    }
    
    private async Task SendPrintStatusAsync(int jobId, string status, string message)
    {
        var statusMsg = new
        {
            type = "print_status",
            timestamp = DateTime.UtcNow.ToString("O"),
            job_id = jobId,
            status = status,
            message = message
        };
        
        await SendMessageAsync(JsonSerializer.Serialize(statusMsg));
    }
    
    private async Task SendPongAsync()
    {
        var pong = new
        {
            type = "pong",
            timestamp = DateTime.UtcNow.ToString("O")
        };
        
        await SendMessageAsync(JsonSerializer.Serialize(pong));
    }
    
    private async Task SendMessageAsync(string message)
    {
        var bytes = Encoding.UTF8.GetBytes(message);
        await webSocket.SendAsync(
            new ArraySegment<byte>(bytes),
            WebSocketMessageType.Text,
            true,
            CancellationToken.None);
    }
}

// 使用示例
class Program
{
    static async Task Main(string[] args)
    {
        var client = new PrintClient();
        await client.ConnectAsync();
    }
}
```

## 🔧 集成配置

### 1. 服务器端配置

在发财小狗饮品店管理后台：

1. 访问 `http://localhost:5000/admin/print/`
2. 添加打印机配置：
   - 名称：您的打印机名称
   - IP地址：客户端程序所在机器IP
   - 端口：9100（或您的打印机端口）
   - 类型：thermal（热敏）或其他
   - 启用自动打印：是

### 2. 客户端配置

在您的打印软件中：

1. 配置WebSocket连接：`ws://服务器IP:8765`
2. 实现消息处理逻辑
3. 集成您的打印机驱动
4. 处理错误和重连

### 3. 测试流程

1. 启动发财小狗饮品店应用
2. 启动您的打印客户端
3. 在管理后台查看连接状态
4. 创建测试订单
5. 确认订单时选择"启用自动打印"
6. 验证客户端是否收到打印任务

## ⚠️ 注意事项

### 安全考虑
- 生产环境建议使用WSS（加密WebSocket）
- 添加客户端认证机制
- 限制连接来源IP

### 网络配置
- 确保端口8765未被占用
- 防火墙允许WebSocket连接
- 客户端能访问服务器IP

### 错误处理
- 实现连接断开重连机制
- 处理网络异常情况
- 记录详细的错误日志

### 性能优化
- 合理设置心跳间隔
- 控制并发连接数
- 优化消息处理速度

## 📞 技术支持

如需技术支持，请提供：
1. 客户端实现语言和版本
2. 错误日志和异常信息
3. 网络环境描述
4. 打印机型号和驱动信息

---

*让打印对接变得简单高效！*
