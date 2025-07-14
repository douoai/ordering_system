import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, folder='uploads'):
    """保存上传的文件"""
    if file and allowed_file(file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
        # 生成唯一文件名
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        # 确保上传目录存在
        upload_path = os.path.join(current_app.static_folder, folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # 返回相对路径
        return os.path.join(folder, unique_filename).replace('\\', '/')
    
    return None

def delete_uploaded_file(file_path):
    """删除上传的文件"""
    if file_path:
        full_path = os.path.join(current_app.static_folder, file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except OSError:
                pass
    return False
