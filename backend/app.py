#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

"""
Flask PSD 模板处理服务器
优雅、简洁、现代化的PSD模板管理API
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import os
import sys
from pathlib import Path
import traceback

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

from config import CONFIG
from processor_core import processor_core

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 配置
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 最大文件大小
app.config['API_BASE_URL'] = CONFIG["API_BASE_URL"]


def json_error(message: str, status: int = 400, include_success: bool = False, **kwargs):
    """统一错误响应格式，保持兼容当前接口结构。

    - message: 错误信息
    - status: HTTP 状态码
    - include_success: 需要时附带 {"success": False}
    - kwargs: 额外字段
    """
    payload = {'error': message}
    if include_success:
        payload['success'] = False
    if kwargs:
        payload.update(kwargs)
    return jsonify(payload), status

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': 'PSD Processor Server is running',
        'version': '2.0.0',
        'framework': 'Flask'
    })

@app.route('/api/validate', methods=['POST'])
def validate_template():
    """验证PSD模板"""
    try:
        if 'template' not in request.files:
            return json_error('缺少template文件', 400)
        
        template_file = request.files['template']
        if template_file.filename == '':
            return json_error('未选择文件', 400)
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix='.psd', delete=False) as temp_file:
            template_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # 验证PSD文件
            is_valid, result = processor_core.validate_psd(temp_path)
            
            if is_valid:
                return jsonify({
                    'valid': True,
                    'message': 'PSD模板验证成功',
                    'info': result
                })
            else:
                return jsonify({
                    'valid': False,
                    'error': result
                }), 400
                
        finally:
            # 清理临时文件
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"验证PSD时出错: {str(e)}")
        print(traceback.format_exc())
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/upload', methods=['POST'])
def upload_template():
    """上传并保存PSD模板"""
    try:
        if 'template' not in request.files:
            return json_error('缺少template文件', 400)
        
        template_file = request.files['template']
        if template_file.filename == '':
            return json_error('未选择文件', 400)
        
        original_filename = template_file.filename
        print(f"接收到模板上传请求: {original_filename}")
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix='.psd', delete=False) as temp_file:
            template_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # 保存模板
            success, result = processor_core.save_template(temp_path, original_filename)
            
            if success:
                print(f"模板保存成功: {result['id']}")
                return jsonify({
                    'success': True,
                    'data': result,
                    'message': '模板上传并保存成功'
                })
            else:
                print(f"模板保存失败: {result}")
                return json_error(result, 400, include_success=True)
                
        finally:
            # 清理临时文件
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"上传模板时出错: {str(e)}")
        print(traceback.format_exc())
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """获取模板列表"""
    try:
        templates = processor_core.get_templates()
        return jsonify({
            'success': True,
            'data': templates
        })
    except Exception as e:
        print(f"获取模板列表时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/delete', methods=['POST'])
def delete_template(template_id):
    """删除模板"""
    try:
        print(f"删除模板请求: {template_id}")
        
        success, message = processor_core.delete_template(template_id)
        
        if success:
            print(f"模板删除成功: {template_id}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            print(f"模板删除失败: {message}")
            return json_error(message, 400, include_success=True)
            
    except Exception as e:
        print(f"删除模板时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/templates/<template_id>/preview', methods=['GET'])
def get_preview_image(template_id):
    """获取模板预览图"""
    try:
        # 查找模板
        templates = processor_core.get_templates()
        template = None
        for t in templates:
            if t['id'] == template_id:
                template = t
                break
        
        if not template:
            return json_error('模板不存在', 404)
        
        if not template.get('previewImage'):
            return json_error('预览图不存在', 404)
        
        # 构建预览图路径
        preview_path = processor_core.previews_dir / template['previewImage']
        
        if not preview_path.exists():
            return json_error('预览图文件不存在', 404)
        
        return send_file(preview_path, mimetype='image/png')
        
    except Exception as e:
        print(f"获取预览图时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/reference', methods=['GET'])
def get_reference_image(template_id):
    """获取模板编辑参考图"""
    try:
        # 查找模板
        templates = processor_core.get_templates()
        template = None
        for t in templates:
            if t['id'] == template_id:
                template = t
                break
        
        if not template:
            return json_error('模板不存在', 404)
        
        if not template.get('referenceImage'):
            return json_error('参考图不存在', 404)
        
        # 构建参考图路径
        reference_path = processor_core.references_dir / template['referenceImage']
        
        if not reference_path.exists():
            return json_error('参考图文件不存在', 404)
        
        return send_file(reference_path, mimetype='image/png')

    except Exception as e:
        print(f"获取参考图时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/generate', methods=['POST'])
def generate_final_psd():
    """生成最终PSD文件"""
    try:
        if 'image' not in request.files:
            return json_error('缺少图片文件', 400)
        
        if 'templateId' not in request.form:
            return json_error('缺少模板ID', 400)
        
        image_file = request.files['image']
        template_id = request.form['templateId']
        force_resize = request.form.get('forceResize', 'false').lower() == 'true'
        selected_component_id = request.form.get('componentId')  # 可选的部件ID
        
        if image_file.filename == '':
            return json_error('未选择图片', 400)
        
        print(f"接收到生成请求:")
        print(f"  模板ID: {template_id}")
        print(f"  图片文件: {image_file.filename}")
        print(f"  强制调整尺寸: {force_resize}")
        print(f"  选择的部件ID: {selected_component_id}")
        
        # 检查模板是否存在
        template = processor_core.get_template_by_id(template_id)
        if not template:
            return json_error('模板不存在', 404)
        
        if not template.get('restoredFileName'):
            return json_error('模板缺少变换结果文件', 400)
        
        # 保存上传的图片到临时文件
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            image_file.save(temp_file.name)
            temp_image_path = temp_file.name
        
        try:
            # 调用生成流程
            success, result = processor_core.generate_final_psd(template_id, temp_image_path, force_resize, selected_component_id)
            
            if success:
                print(f"生成成功: {result}")
                return jsonify({
                    'success': True,
                    'data': result,
                    'message': '生成成功'
                })
            else:
                print(f"生成失败: {result}")
                return json_error(result, 500, include_success=True)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)
            
    except Exception as e:
        print(f"生成PSD时出错: {str(e)}")
        print(traceback.format_exc())
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/results/<result_id>/download', methods=['GET'])
def download_final_psd(result_id):
    """下载最终生成的PSD文件"""
    try:
        final_psd_path = processor_core.result_downloads_dir / f"{result_id}_final.psd"
        
        if not final_psd_path.exists():
            return json_error('文件不存在', 404)
        
        return send_file(
            final_psd_path,
            as_attachment=True,
            download_name=f"{result_id}_final.psd",
            mimetype="application/octet-stream"
        )
        
    except Exception as e:
        print(f"下载PSD文件时出错: {str(e)}")
        return json_error(f'下载失败: {str(e)}', 500)

@app.route('/api/results/<result_id>/preview', methods=['GET'])
def get_final_preview(result_id):
    """获取最终结果的预览图"""
    try:
        preview_path = processor_core.result_previews_dir / f"{result_id}_final_preview.png"
        
        if not preview_path.exists():
            return json_error('预览图不存在', 404)
        
        return send_file(
            preview_path,
            mimetype="image/png"
        )
        
    except Exception as e:
        print(f"获取预览图时出错: {str(e)}")
        return json_error(f'获取预览图失败: {str(e)}', 500)

@app.route('/api/process', methods=['POST'])
def process_psd():
    """处理PSD文件"""
    try:
        # 检查必要文件
        if 'template' not in request.files:
            return json_error('缺少template文件', 400)
        
        if 'source_image' not in request.files:
            return json_error('缺少source_image文件', 400)
        
        template_file = request.files['template']
        source_file = request.files['source_image']
        
        print(f"接收到处理请求:")
        print(f"  模板文件: {template_file.filename}")
        print(f"  源图片: {source_file.filename}")
        
        # 创建临时目录处理文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存上传的文件
            template_path = os.path.join(temp_dir, "template.psd")
            source_path = os.path.join(temp_dir, f"source.{source_file.filename.split('.')[-1]}")
            output_path = os.path.join(temp_dir, "result.psd")
            
            # 保存文件
            template_file.save(template_path)
            source_file.save(source_path)
            
            print("开始处理PSD...")
            
            # 调用处理器
            success, message = processor_core.process_psd(
                template_path, source_path, output_path
            )
            
            if success:
                print("PSD处理成功，返回结果文件")
                # 发送处理后的PSD文件
                return send_file(
                    output_path, 
                    as_attachment=True,
                    download_name="result.psd",
                    mimetype="application/octet-stream"
                )
            else:
                print(f"PSD处理失败: {message}")
                return json_error(f'处理失败: {message}', 500)
                
    except Exception as e:
        error_msg = f"处理PSD时出错: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return json_error(f'服务器错误: {str(e)}', 500)

# ===== 部件管理相关API =====

@app.route('/api/templates/<template_id>/components', methods=['POST'])
def upload_component(template_id):
    """上传部件到模板"""
    try:
        # 检查是否有文件上传
        if 'component' not in request.files:
            return json_error('未选择部件文件', 400)
        
        file = request.files['component']
        if file.filename == '':
            return json_error('未选择部件文件', 400)
        
        # 获取部件名称，默认使用文件名
        component_name = request.form.get('name', Path(file.filename).stem)
        
        print(f"接收到部件上传请求:")
        print(f"  模板ID: {template_id}")
        print(f"  部件文件: {file.filename}")
        print(f"  部件名称: {component_name}")
        
        # 获取模板的现有部件，确保名称唯一
        existing_components = processor_core.get_template_components(template_id)
        unique_name = processor_core.generate_unique_component_name(component_name, existing_components)
        
        # 保存部件
        success, result = processor_core.save_component(template_id, file, unique_name)
        
        if success:
            return jsonify({
                'success': True,
                'data': result,
                'message': '部件上传成功'
            })
        else:
            return json_error(result, 400)
            
    except Exception as e:
        print(f"上传部件时出错: {str(e)}")
        print(traceback.format_exc())
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/components', methods=['GET'])
def get_components(template_id):
    """获取模板的所有部件"""
    try:
        components = processor_core.get_template_components(template_id)
        return jsonify({
            'success': True,
            'data': components
        })
    except Exception as e:
        print(f"获取部件列表时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/components/<component_id>', methods=['GET'])
def get_component_image(template_id, component_id):
    """获取部件图片"""
    try:
        component_path = processor_core.get_component_file_path(template_id, component_id)
        
        if not component_path or not component_path.exists():
            return json_error('部件文件不存在', 404)
        
        return send_file(component_path, mimetype='image/png')
        
    except Exception as e:
        print(f"获取部件图片时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/components/<component_id>', methods=['PUT'])
def update_component(template_id, component_id):
    """更新部件名称"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return json_error('缺少部件名称', 400)
        
        new_name = data['name'].strip()
        if not new_name:
            return json_error('部件名称不能为空', 400)
        
        success, result = processor_core.update_component_name(template_id, component_id, new_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': result
            })
        else:
            return json_error(result, 400)
            
    except Exception as e:
        print(f"更新部件名称时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/api/templates/<template_id>/components/<component_id>', methods=['DELETE'])
def delete_component(template_id, component_id):
    """删除部件"""
    try:
        success, result = processor_core.delete_component(template_id, component_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': result
            })
        else:
            return json_error(result, 400)
            
    except Exception as e:
        print(f"删除部件时出错: {str(e)}")
        return json_error(f'服务器错误: {str(e)}', 500)

@app.route('/')
def index():
    """主页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PSD Processor Server (Flask)</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            code { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
            ul { line-height: 1.6; }
        </style>
    </head>
    <body>
        <h1>[TARGET] PSD Processor Server (Flask)</h1>
        <p>优雅、简洁、现代化的PSD模板处理服务器正在运行</p>
        <h2>API端点:</h2>
        <ul>
            <li><code>GET /api/health</code> - 健康检查</li>
            <li><code>POST /api/validate</code> - 验证PSD模板</li>
            <li><code>POST /api/upload</code> - 上传并保存PSD模板</li>
            <li><code>GET /api/templates</code> - 获取模板列表</li>
            <li><code>GET /api/templates/{id}/preview</code> - 获取模板预览图</li>
            <li><code>GET /api/templates/{id}/reference</code> - 获取模板编辑参考图</li>
            <li><code>POST /api/templates/{id}/delete</code> - 删除模板</li>
            <li><code>POST /api/process</code> - 处理PSD文件</li>
        </ul>
        <p><small>Flask框架 | 跨域支持 | 现代化API设计</small></p>
    </body>
    </html>
    """

@app.errorhandler(413)
def too_large(e):
    """文件过大错误处理"""
    return jsonify({
        'error': '上传文件过大，最大支持100MB'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """404错误处理"""
    return jsonify({
        'error': 'API端点不存在'
    }), 404

@app.errorhandler(500)
def server_error(e):
    """500错误处理"""
    return jsonify({
        'error': '服务器内部错误'
    }), 500

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Flask PSD Processor Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8012, help='Port number (default: 8012)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # 取消对 scripts 目录与脚本文件的依赖检查（后端使用内部模块）
    
    print("=" * 60)
    print("[START] Flask PSD Processor Server Starting...")
    print("=" * 60)
    print(f"[INFO] Active environment: {CONFIG['ENV']}")
    public_domain = CONFIG["DOMAIN"]
    print(f"[INFO] Server address: http://{args.host}:{args.port}")
    print(f"[INFO] Public domain: {public_domain}")
    print(f"[INFO] Homepage: http://{public_domain}:{args.port}/")
    print(f"[INFO] Health check: http://{public_domain}:{args.port}/api/health")
    print(f"[CONFIG] API endpoints:")
    print(f"   POST /api/validate - Validate PSD template")
    print(f"   POST /api/upload - Upload and save PSD template")
    print(f"   GET /api/templates - Get template list")
    print(f"   GET /api/templates/{{id}}/preview - Get template preview image")
    print(f"   GET /api/templates/{{id}}/reference - Get template reference image")
    print(f"   POST /api/templates/{{id}}/delete - Delete template")
    print(f"   POST /api/process - Process PSD file")
    print("=" * 60)
    print("[FEATURES]:")
    print("   + Flask framework - Modern web framework")
    print("   + CORS support - Complete CORS configuration")
    print("   + Error handling - Graceful exception handling")
    print("   + File upload - Support for large file uploads")
    print("=" * 60)
    print("Press Ctrl+C to stop server")
    print()
    
    try:
        # 启动Flask应用
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("[STOP] Server stopped")
        print("[GOODBYE] Goodbye!")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR] Server startup failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
