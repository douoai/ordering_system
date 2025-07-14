#!/usr/bin/env python3
"""
打印管理路由
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.models import db, PrinterConfig, PrintJob, Order
from app.admin.routes import admin_required
from app.websocket.print_server import print_server, get_print_server_status
from datetime import datetime
import json
import asyncio

bp = Blueprint('print_admin', __name__, url_prefix='/admin/print')

@bp.route('/')
@admin_required
def index():
    """打印管理首页"""
    # 获取打印机列表
    printers = PrinterConfig.query.all()
    
    # 获取最近的打印任务
    recent_jobs = PrintJob.query.order_by(PrintJob.created_at.desc()).limit(10).all()
    
    # 获取打印服务器状态
    server_status = get_print_server_status()
    
    # 统计信息
    stats = {
        'total_printers': PrinterConfig.query.count(),
        'active_printers': PrinterConfig.query.filter_by(is_active=True).count(),
        'pending_jobs': PrintJob.query.filter_by(status='pending').count(),
        'failed_jobs': PrintJob.query.filter_by(status='failed').count(),
        'completed_today': PrintJob.query.filter(
            PrintJob.status == 'completed',
            PrintJob.completed_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
    }
    
    return render_template('admin/print/index.html', 
                         printers=printers, 
                         recent_jobs=recent_jobs,
                         server_status=server_status,
                         stats=stats)

@bp.route('/printers')
@admin_required
def printers():
    """打印机管理"""
    printers = PrinterConfig.query.all()
    return render_template('admin/print/printers.html', printers=printers)

@bp.route('/printers/add', methods=['GET', 'POST'])
@admin_required
def add_printer():
    """添加打印机"""
    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        port = request.form.get('port', 9100, type=int)
        printer_type = request.form.get('printer_type', 'thermal')
        paper_width = request.form.get('paper_width', 80, type=int)
        auto_print_orders = request.form.get('auto_print_orders') == 'on'
        print_copies = request.form.get('print_copies', 1, type=int)
        description = request.form.get('description')
        
        if not name:
            flash('请输入打印机名称', 'error')
            return render_template('admin/print/add_printer.html')
        
        printer = PrinterConfig(
            name=name,
            ip_address=ip_address,
            port=port,
            printer_type=printer_type,
            paper_width=paper_width,
            auto_print_orders=auto_print_orders,
            print_copies=print_copies,
            description=description
        )
        
        db.session.add(printer)
        db.session.commit()
        
        flash(f'打印机 "{name}" 添加成功', 'success')
        return redirect(url_for('print_admin.printers'))
    
    return render_template('admin/print/add_printer.html')

@bp.route('/printers/<int:printer_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_printer(printer_id):
    """编辑打印机"""
    printer = PrinterConfig.query.get_or_404(printer_id)
    
    if request.method == 'POST':
        printer.name = request.form.get('name')
        printer.ip_address = request.form.get('ip_address')
        printer.port = request.form.get('port', 9100, type=int)
        printer.printer_type = request.form.get('printer_type', 'thermal')
        printer.paper_width = request.form.get('paper_width', 80, type=int)
        printer.auto_print_orders = request.form.get('auto_print_orders') == 'on'
        printer.print_copies = request.form.get('print_copies', 1, type=int)
        printer.description = request.form.get('description')
        printer.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'打印机 "{printer.name}" 更新成功', 'success')
        return redirect(url_for('print_admin.printers'))
    
    return render_template('admin/print/edit_printer.html', printer=printer)

@bp.route('/printers/<int:printer_id>/toggle')
@admin_required
def toggle_printer(printer_id):
    """启用/禁用打印机"""
    printer = PrinterConfig.query.get_or_404(printer_id)
    printer.is_active = not printer.is_active
    printer.updated_at = datetime.utcnow()

    db.session.commit()

    status = "启用" if printer.is_active else "禁用"
    flash(f'打印机 "{printer.name}" 已{status}', 'success')

    return redirect(url_for('print_admin.printers'))

@bp.route('/jobs')
@admin_required
def jobs():
    """打印任务管理"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = PrintJob.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    jobs = query.order_by(PrintJob.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/print/jobs.html', jobs=jobs, status_filter=status_filter)

@bp.route('/jobs/<int:job_id>/retry')
@admin_required
def retry_job(job_id):
    """重试打印任务"""
    job = PrintJob.query.get_or_404(job_id)

    if not job.can_retry:
        flash('该任务无法重试', 'error')
        return redirect(url_for('print_admin.jobs'))

    job.status = 'pending'
    job.error_message = None
    db.session.commit()

    # 尝试重新发送到打印机
    try:
        asyncio.run(send_print_job_to_printer(job))
        flash(f'打印任务 #{job.id} 已重新发送', 'success')
    except Exception as e:
        flash(f'重新发送失败: {str(e)}', 'error')

    return redirect(url_for('print_admin.jobs'))

@bp.route('/jobs/<int:job_id>/cancel')
@admin_required
def cancel_job(job_id):
    """取消打印任务"""
    job = PrintJob.query.get_or_404(job_id)

    if job.status in ['completed', 'cancelled']:
        flash('该任务无法取消', 'error')
        return redirect(url_for('print_admin.jobs'))

    job.status = 'cancelled'
    db.session.commit()

    flash(f'打印任务 #{job.id} 已取消', 'success')
    return redirect(url_for('print_admin.jobs'))

@bp.route('/server/status')
@admin_required
def server_status():
    """获取服务器状态"""
    status = get_print_server_status()
    return jsonify(status)

@bp.route('/server/restart')
@admin_required
def restart_server():
    """重启打印服务器"""
    try:
        # 这里可以添加重启服务器的逻辑
        flash('打印服务器重启请求已发送', 'info')
    except Exception as e:
        flash(f'重启失败: {str(e)}', 'error')

    return redirect(url_for('print_admin.index'))

@bp.route('/test/print')
@admin_required
def test_print():
    """测试打印"""
    test_data = {
        "type": "test_print",
        "content": "发财小狗饮品店\n测试打印\n" + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # 发送测试打印命令
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(print_server.send_print_command(test_data))
        
        if success:
            flash('测试打印命令已发送', 'success')
        else:
            flash('没有连接的打印客户端', 'warning')
    except Exception as e:
        flash(f'测试打印失败: {str(e)}', 'error')
    
    return redirect(url_for('print_admin.index'))

async def send_print_job_to_printer(job):
    """发送打印任务到打印机"""
    try:
        # 构建打印数据
        print_data = {
            "job_id": job.id,
            "order_id": job.order_id,
            "type": job.job_type,
            "content": job.print_content,
            "copies": job.copies,
            "printer_config": {
                "paper_width": job.printer.paper_width if job.printer else 80,
                "printer_type": job.printer.printer_type if job.printer else "thermal"
            }
        }
        
        # 标记为正在打印
        job.mark_as_printing()
        db.session.commit()
        
        # 发送到打印服务器
        success = await print_server.send_print_command(print_data)
        
        if success:
            job.mark_as_completed()
        else:
            job.mark_as_failed("没有可用的打印客户端")
        
        db.session.commit()
        return success
        
    except Exception as e:
        job.mark_as_failed(str(e))
        db.session.commit()
        raise e
