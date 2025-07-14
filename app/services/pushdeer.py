"""
PushDeer推送服务
"""
import requests
import json
from typing import Optional, Dict, Any
from app.models import db, PushDeerConfig, PushRecord
from datetime import datetime


class PushDeerService:
    """PushDeer推送服务类"""
    
    def __init__(self):
        self.timeout = 10  # 请求超时时间
    
    def send_message(self, config_id: int, text: str, desp: str = '',
                    message_type: str = 'text', event_type: str = 'manual',
                    order_id: int = None) -> Dict[str, Any]:
        """
        发送推送消息

        Args:
            config_id: 配置ID
            text: 消息标题/内容
            desp: 消息详情（可选）
            message_type: 消息类型 (text, markdown, image)
            event_type: 事件类型
            order_id: 关联订单ID（可选）

        Returns:
            Dict: 推送结果
        """
        # 验证config_id
        if config_id is None:
            return {
                'success': False,
                'error': 'config_id不能为空'
            }

        config = PushDeerConfig.query.get(config_id)
        if not config or not config.is_active:
            return {
                'success': False,
                'error': '配置不存在或已禁用'
            }

        # 创建推送记录
        try:
            push_record = PushRecord(
                config_id=config_id,
                order_id=order_id,
                event_type=event_type,
                title=text,
                content=desp,
                status='pending'
            )
            db.session.add(push_record)
            db.session.flush()  # 获取记录ID
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'创建推送记录失败: {str(e)}'
            }

        # 发送推送
        result = self._send_to_pushdeer(
            endpoint=config.endpoint,
            pushkey=config.pushkey,
            text=text,
            desp=desp,
            message_type=message_type
        )

        # 更新推送记录
        push_record.sent_at = datetime.utcnow()
        if result['success']:
            push_record.status = 'success'
            push_record.set_response_data(result.get('data', {}))
        else:
            push_record.status = 'failed'
            push_record.error_message = result.get('error', '未知错误')

        db.session.commit()

        return result
    
    def send_message_by_key(self, pushkey: str, text: str, desp: str = '',
                           message_type: str = 'text', 
                           endpoint: str = 'https://api2.pushdeer.com') -> Dict[str, Any]:
        """
        直接通过pushkey发送消息
        
        Args:
            pushkey: PushDeer推送密钥
            text: 消息标题/内容
            desp: 消息详情（可选）
            message_type: 消息类型 (text, markdown, image)
            endpoint: API端点
            
        Returns:
            Dict: 推送结果
        """
        return self._send_to_pushdeer(endpoint, pushkey, text, desp, message_type)
    
    def _send_to_pushdeer(self, endpoint: str, pushkey: str, text: str,
                         desp: str = '', message_type: str = 'text') -> Dict[str, Any]:
        """
        发送消息到PushDeer

        Args:
            endpoint: API端点
            pushkey: 推送密钥
            text: 消息内容
            desp: 消息详情
            message_type: 消息类型

        Returns:
            Dict: 推送结果
        """
        try:
            # 构建API URL
            url = f"{endpoint.rstrip('/')}/message/push"

            # 构建请求参数
            params = {
                'pushkey': pushkey,
                'text': text,
                'type': message_type
            }

            if desp:
                params['desp'] = desp

            # 使用GET请求发送（更简单可靠）
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'PushDeer-DrinkShop/1.0'
                }
            )
            
            # 解析响应
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('code') == 0:
                        return {
                            'success': True,
                            'message': '推送成功',
                            'data': result.get('content', {})
                        }
                    else:
                        return {
                            'success': False,
                            'error': result.get('error', '推送失败'),
                            'code': result.get('code')
                        }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': '响应格式错误'
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '请求超时'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': '连接失败'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'未知错误: {str(e)}'
            }
    
    def test_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试配置是否有效

        Args:
            config_id: 配置ID

        Returns:
            Dict: 测试结果
        """
        return self.send_message(
            config_id=config_id,
            text='🧪 PushDeer配置测试',
            desp='这是一条来自小狗发财饮品店的测试消息，如果您收到此消息，说明配置正确！',
            message_type='markdown',
            event_type='test'
        )
    
    def test_key(self, pushkey: str, endpoint: str = 'https://api2.pushdeer.com') -> Dict[str, Any]:
        """
        测试pushkey是否有效
        
        Args:
            pushkey: 推送密钥
            endpoint: API端点
            
        Returns:
            Dict: 测试结果
        """
        return self.send_message_by_key(
            pushkey=pushkey,
            text='🧪 PushDeer密钥测试',
            desp='这是一条来自小狗发财饮品店的测试消息，如果您收到此消息，说明密钥配置正确！',
            message_type='markdown',
            endpoint=endpoint
        )
    
    def send_order_notification(self, order, event_type: str = 'new_order'):
        """
        发送订单相关通知

        Args:
            order: 订单对象
            event_type: 事件类型 (new_order, order_confirmed, order_cancelled, order_refunded, cancel_request, cancel_approved, cancel_rejected, refund_request, refund_approved, refund_rejected, refund_completed)
        """
        # 获取所有启用的配置
        configs = PushDeerConfig.query.filter_by(is_active=True).all()

        for config in configs:
            events_config = config.get_events_config()

            # 检查是否启用了该事件类型的推送
            if not events_config.get(event_type, False):
                continue
            
            # 根据事件类型构建消息
            if event_type == 'new_order':
                text = f"🆕 新订单 #{order.id}"
                desp = f"""
**客户信息：**
- 姓名：{order.user.username}
- 电话：{order.user.phone or '未提供'}

**订单详情：**
- 订单号：{order.id}
- 总金额：¥{order.total_amount:.2f}
- 下单时间：{order.created_at.strftime('%Y-%m-%d %H:%M:%S')}

**订单项目：**
"""
                for item in order.order_items:
                    desp += f"- {item.drink_product.name} x{item.quantity} (¥{item.subtotal:.2f})\n"

                if order.notes:
                    desp += f"\n**备注：** {order.notes}"
                    
            elif event_type == 'order_confirmed':
                text = f"✅ 订单已确认 #{order.id}"
                desp = f"""
订单 #{order.id} 已确认，客户：{order.user.username}
总金额：¥{order.total_amount:.2f}
确认时间：{order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if order.confirmed_at else '刚刚'}
"""
            elif event_type == 'order_cancelled':
                text = f"❌ 订单已取消 #{order.id}"
                desp = f"""
订单 #{order.id} 已取消，客户：{order.user.username}
原金额：¥{order.total_amount:.2f}
取消时间：{order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if order.confirmed_at else '刚刚'}
"""
            elif event_type == 'order_refunded':
                text = f"💰 订单申请退款 #{order.id}"
                desp = f"""
**退款申请详情：**
- 订单号：{order.id}
- 客户：{order.user.username}
- 电话：{order.user.phone or '未提供'}
- 退款金额：¥{order.total_amount:.2f}
- 申请时间：{order.refunded_at.strftime('%Y-%m-%d %H:%M:%S') if order.refunded_at else '刚刚'}

**退款原因：**
{order.refund_reason or '未提供'}

**订单项目：**
"""
                for item in order.order_items:
                    desp += f"- {item.drink_product.name} x{item.quantity} (¥{item.subtotal:.2f})\n"

                desp += f"\n**原订单时间：** {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            elif event_type == 'refund_request':
                text = f"💰 新退款申请 #{order.id}"
                desp = f"""
**退款申请详情：**
- 订单号：{order.id}
- 客户：{order.user.username}
- 电话：{order.user.phone or '未提供'}
- 退款金额：¥{order.total_amount:.2f}
- 申请时间：{order.refunded_at.strftime('%Y-%m-%d %H:%M:%S') if order.refunded_at else '刚刚'}

**退款原因：**
{order.refund_reason or '未提供'}

**订单状态：** {order.status_display}
**需要审批：** {'是' if order.needs_refund_approval else '否'}
"""
                if order.refund_qr_code:
                    desp += f"\n**收款二维码：** 已上传"

            elif event_type == 'refund_approved':
                text = f"✅ 退款已批准 #{order.id}"
                desp = f"""
**退款批准通知：**
- 订单号：{order.id}
- 客户：{order.user.username}
- 退款金额：¥{order.total_amount:.2f}
- 批准人：{order.refund_approved_by}
- 批准时间：{order.refund_approved_at.strftime('%Y-%m-%d %H:%M:%S') if order.refund_approved_at else '刚刚'}

**请尽快为用户打款！**
"""
                if order.refund_admin_notes:
                    desp += f"\n**管理员备注：** {order.refund_admin_notes}"

            elif event_type == 'refund_rejected':
                text = f"❌ 退款已拒绝 #{order.id}"
                desp = f"""
**退款拒绝通知：**
- 订单号：{order.id}
- 客户：{order.user.username}
- 退款金额：¥{order.total_amount:.2f}
- 处理人：{order.refund_approved_by}
- 处理时间：{order.refund_approved_at.strftime('%Y-%m-%d %H:%M:%S') if order.refund_approved_at else '刚刚'}

**拒绝原因：** {order.refund_admin_notes or '未提供'}
"""
            elif event_type == 'refund_completed':
                text = f"💸 退款已完成 #{order.id}"
                desp = f"""
**退款完成通知：**
- 订单号：{order.id}
- 客户：{order.user.username}
- 退款金额：¥{order.total_amount:.2f}
- 完成时间：{order.refund_completed_at.strftime('%Y-%m-%d %H:%M:%S') if order.refund_completed_at else '刚刚'}

**退款流程已全部完成！**
"""
            else:
                continue
            
            # 发送推送
            try:
                if config.id is None:
                    print(f"警告: 配置 {config.name} 的ID为空，跳过推送")
                    continue

                result = self.send_message(
                    config_id=config.id,
                    text=text,
                    desp=desp,
                    message_type='markdown',
                    event_type=event_type,
                    order_id=order.id
                )

                if not result['success']:
                    print(f"推送失败: {result.get('error', '未知错误')}")

            except Exception as e:
                print(f"发送推送时出错: {e}")
                import traceback
                traceback.print_exc()


# 创建全局实例
pushdeer_service = PushDeerService()
