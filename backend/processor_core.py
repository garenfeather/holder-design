#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PSD处理核心模块
整合psd_replacer和transform_template_final的功能
"""

# 标准库导入
import sys
import os
import json
import shutil
import time
import tempfile
import struct
import io
import glob
import traceback
from pathlib import Path
from datetime import datetime

# 第三方库导入
from PIL import Image, ImageFilter
from psd_tools import PSDImage

# 本地模块导入
from integrated_processor import IntegratedProcessor
from transformer_inside import InsideTransformer
from psd_cropper import PSDCropper
from psd_resizer import PSDResizerV2
from psd_transformer import BinaryPSDTransformer
from psd_replacer import PSDReplacer
from psd_scaler import PSDScaler
from png_stroke_processor import PNGStrokeProcessor
from utils.strings import sanitize_name
from config import get_storage_root

class PSDProcessorCore:
    """PSD处理核心类"""
    
    def __init__(self):
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]
        storage_root = get_storage_root()
        self.templates_dir = storage_root / "templates"
        self.inside_dir = storage_root / "inside"
        self.inside_stroke_v2_dir = storage_root / "inside_stroke_v2"
        self.previews_dir = storage_root / "previews"
        self.references_dir = storage_root / "references"
        self.components_dir = storage_root / "components"
        # 新的result目录结构
        self.results_dir = storage_root / "results"
        self.result_previews_dir = self.results_dir / "previews"
        self.result_downloads_dir = self.results_dir / "downloads"
        # 保留temp_dir的引用以兼容现有代码，实际指向results目录
        self.temp_dir = self.results_dir
        self.templates_index_file = self.templates_dir / "templates.json"
        self.results_index_file = self.results_dir / "results_index.json"
        self._ensure_storage_dirs()
    
    def validate_psd(self, psd_path):
        """验证PSD文件是否包含必要图层"""
        try:
            psd = PSDImage.open(psd_path)
            found_layers = set()
            
            for layer in psd:
                layer_name = sanitize_name(layer.name).lower()
                if layer_name in self.required_layers:
                    found_layers.add(layer_name)
            
            missing_layers = set(self.required_layers) - found_layers
            
            if missing_layers:
                return False, f"缺少必要图层: {', '.join(missing_layers)}"
            
            return True, {
                'width': psd.width,
                'height': psd.height,
                'layers': list(found_layers)
            }
            
        except Exception as e:
            return False, f"PSD文件解析失败: {str(e)}"
    
    def get_psd_info(self, psd_path):
        """获取PSD文件基本信息"""
        try:
            psd = PSDImage.open(psd_path)
            info = {
                'width': psd.width,
                'height': psd.height,
                'layer_count': len(list(psd)),
                'layers': [sanitize_name(layer.name) for layer in psd]
            }
            
            # 获取view层的尺寸信息
            view_info = self._get_view_layer_info(psd)
            if view_info:
                info['viewLayer'] = view_info
                
            return info
        except Exception as e:
            return None
    
    def _get_view_layer_info(self, psd):
        """获取view层的详细信息"""
        try:
            for layer in psd:
                if sanitize_name(layer.name).lower() == 'view':
                    return {
                        'width': layer.width,
                        'height': layer.height,
                        'left': layer.left,
                        'top': layer.top,
                        'right': layer.right,
                        'bottom': layer.bottom
                    }
            return None
        except Exception as e:
            print(f"Failed to get view layer info: {e}")
            return None
    
    def process_psd(self, template_path, source_image_path, output_path):
        """处理PSD文件"""
        try:
            # 首先验证模板
            is_valid, result = self.validate_psd(template_path)
            if not is_valid:
                return False, result
            
            # 调用integrated_processor进行处理
            processor = IntegratedProcessor(template_path, source_image_path, output_path)
            success = processor.process()
            
            if success:
                return True, "处理成功"
            else:
                return False, "PSD处理失败"
                
        except Exception as e:
            return False, f"处理过程中出错: {str(e)}"
    
    def _ensure_storage_dirs(self):
        """确保存储目录存在"""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.inside_dir.mkdir(parents=True, exist_ok=True)
        self.inside_stroke_v2_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)
        self.references_dir.mkdir(parents=True, exist_ok=True)
        self.components_dir.mkdir(parents=True, exist_ok=True)
        # 创建新的results目录结构
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.result_previews_dir.mkdir(parents=True, exist_ok=True)
        self.result_downloads_dir.mkdir(parents=True, exist_ok=True)
        if not self.templates_index_file.exists():
            self._save_templates_index([])

    def _cleanup_temp_files(self, result_id):
        """清理生成过程中的临时文件，只保留最终的PSD和预览图"""
        try:
            temp_files = [
                f"{result_id}_result.psd",               # 中间步骤PSD
                f"{result_id}_step1_aligned_image.png",  # 对齐后的源图片
                f"{result_id}_step1_aligned_template.psd"  # 对齐后的模板（如果存在）
            ]

            cleanup_count = 0
            for temp_file in temp_files:
                temp_path = self.temp_dir / temp_file
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                        cleanup_count += 1
                        print(f"已清理临时文件: {temp_file}")
                    except Exception as e:
                        print(f"清理文件失败 {temp_file}: {e}")

            if cleanup_count > 0:
                print(f"临时文件清理完成，共清理 {cleanup_count} 个文件")

        except Exception as e:
            print(f"清理临时文件时出错: {e}")
    
    def _load_templates_index(self):
        """加载模板索引"""
        try:
            if self.templates_index_file.exists():
                with open(self.templates_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_templates_index(self, templates):
        """保存模板索引"""
        try:
            with open(self.templates_index_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save template index: {e}")

    def _update_template_record(self, template_id, updater):
        """原子更新单个模板记录（就地修改并保存索引）"""
        templates = self._load_templates_index()
        changed = False
        for i, t in enumerate(templates):
            if t.get('id') == template_id:
                new_t = updater(dict(t))
                templates[i] = new_t
                changed = True
                break
        if changed:
            self._save_templates_index(templates)
        return changed
    
    def _get_unique_filename(self, original_filename):
        """获取唯一文件名，如果同名则添加-1, -2等后缀"""
        base_path = Path(original_filename)
        base_name = base_path.stem
        extension = base_path.suffix
        
        # 检查现有模板
        existing_templates = self._load_templates_index()
        existing_names = {template['fileName'] for template in existing_templates}
        
        if original_filename not in existing_names:
            return original_filename
        
        # 寻找可用的编号后缀
        counter = 1
        while True:
            new_filename = f"{base_name}-{counter}{extension}"
            if new_filename not in existing_names:
                return new_filename
            counter += 1
    
    def _generate_preview_image(self, psd_path, template_id):
        """生成模板预览图：按part选区填充50%灰，并裁切透明边"""
        try:
            psd = PSDImage.open(psd_path)
            canvas_width, canvas_height = psd.width, psd.height
            
            # 查找part图层
            part_layers = []
            for layer in psd:
                if sanitize_name(layer.name).lower().startswith('part'):
                    part_layers.append(layer)
            
            if not part_layers:
                # 如果没有part图层，创建简单的灰色图（不裁切）
                gray_img = Image.new('RGBA', (canvas_width, canvas_height), (128, 128, 128, 255))
            else:
                # 创建透明背景
                result_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                
                # 先合并所有part图层到一个统一的图层
                merged_layer = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                
                for layer in part_layers:
                    try:
                        # 获取图层图像
                        layer_img = layer.topil()
                        if layer_img.mode != 'RGBA':
                            layer_img = layer_img.convert('RGBA')
                        
                        # 获取图层位置
                        left = getattr(layer, 'left', 0)
                        top = getattr(layer, 'top', 0)
                        
                        # 将图层内容粘贴到正确位置
                        if layer_img.size[0] > 0 and layer_img.size[1] > 0:
                            # 确保坐标在画布范围内
                            paste_left = max(0, min(left, canvas_width))
                            paste_top = max(0, min(top, canvas_height))
                            
                            # 计算实际粘贴区域
                            layer_width = min(layer_img.size[0], canvas_width - paste_left)
                            layer_height = min(layer_img.size[1], canvas_height - paste_top)
                            
                            if layer_width > 0 and layer_height > 0:
                                # 裁剪图层到合适大小
                                cropped_layer = layer_img.crop((0, 0, layer_width, layer_height))
                                merged_layer.paste(cropped_layer, (paste_left, paste_top), cropped_layer)
                        
                    except Exception as layer_error:
                        print(f"Error processing layer: {layer_error}")
                        continue
                
                # 获取合并图层的选区（alpha通道）并填充50%灰色
                _, _, _, alpha = merged_layer.split()
                gray_overlay = Image.new('RGBA', (canvas_width, canvas_height), (128, 128, 128, 255))
                result_img.paste(gray_overlay, mask=alpha)
                
                # 透明边裁切
                bbox = alpha.getbbox()
                gray_img = result_img.crop(bbox) if bbox else result_img
            
            # 保存预览图
            preview_filename = f"{template_id}_preview.png"
            preview_path = self.previews_dir / preview_filename
            gray_img.save(preview_path, 'PNG')
            
            print(f"Preview generation successful: {preview_filename} ({canvas_width}x{canvas_height})")
            return True, preview_filename
            
        except Exception as e:
            print(f"Preview generation failed: {e}")
            print(traceback.format_exc())
            return False, str(e)
    
    def _generate_restored_psd(self, psd_path, template_id):
        """对原始PSD进行逆展开变换和裁剪，生成b.psd"""
        try:
            
            print(f"Starting restored PSD generation, template ID: {template_id}", flush=True, file=sys.stderr)
            
            restored_filename = f"{template_id}_restored.psd"
            restored_path = self.inside_dir / restored_filename
            
            # 步骤1: 使用InsideTransformer进行逆展开变换
            temp_dir = tempfile.mkdtemp()
            temp_transformed_path = Path(temp_dir) / f"{template_id}_inside_temp_transformed.psd"
            
            transformer = InsideTransformer()
            transform_success = transformer.transform(str(psd_path), str(temp_transformed_path))

            if not transform_success:
                # 清理临时文件
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise Exception("InsideTransformer failed")

            # 步骤2: 使用PSDCropper进行裁剪
            print(f"Starting crop to view size...", flush=True, file=sys.stderr)
            cropper = PSDCropper()
            crop_success = cropper.crop_by_view(str(temp_transformed_path), str(restored_path))
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if not crop_success:
                raise Exception("PSDCropper failed")

            print(f"Restored PSD generation successful: {restored_filename}", flush=True, file=sys.stderr)
            return True, restored_filename

        except Exception as e:
            print(f"Restored PSD generation failed: {e}")
            print(traceback.format_exc())
            return False, str(e)

    def _generate_multi_stroke_versions(self, template_id, stroke_widths):
        """生成多个stroke版本的inside PSD

        Args:
            template_id (str): 模板ID
            stroke_widths (list): stroke宽度数组，如 [2, 5, 8]

        Returns:
            tuple: (success, result)
                success (bool): 是否成功
                result (dict): 包含各stroke版本路径的映射
        """
        try:
            print(f"[START] 生成多stroke版本，模板ID: {template_id}", flush=True, file=sys.stderr)
            print(f"[CONFIG] stroke宽度数组: {stroke_widths}", flush=True, file=sys.stderr)

            # 验证输入参数
            if not stroke_widths or not isinstance(stroke_widths, list):
                return False, "stroke_widths参数无效"

            # 验证宽度范围和去重
            valid_widths = []
            for width in stroke_widths:
                if isinstance(width, (int, float)) and 1 <= width <= 10:
                    if width not in valid_widths:
                        valid_widths.append(int(width))

            if not valid_widths:
                return False, "无有效的stroke宽度值"

            # 按大小排序
            valid_widths.sort()
            print(f"[VALIDATED] 有效stroke宽度: {valid_widths}", flush=True, file=sys.stderr)

            # 检查原始inside PSD是否存在
            restored_filename = f"{template_id}_restored.psd"
            original_psd_path = self.inside_dir / restored_filename

            if not original_psd_path.exists():
                return False, f"原始inside PSD不存在: {restored_filename}"

            print(f"[SOURCE] 原始inside PSD: {original_psd_path}", flush=True, file=sys.stderr)

            # 结果收集
            stroke_versions = {}

            # 对每个stroke宽度生成版本
            for width in valid_widths:
                print(f"\\n[STROKE] 开始生成 {width}px stroke版本...", flush=True, file=sys.stderr)

                success, stroke_path = self._generate_single_stroke_version(
                    template_id, width, original_psd_path
                )

                if success:
                    stroke_versions[width] = stroke_path
                    print(f"[SUCCESS] {width}px stroke版本生成完成: {stroke_path}", flush=True, file=sys.stderr)
                else:
                    print(f"[ERROR] {width}px stroke版本生成失败: {stroke_path}", flush=True, file=sys.stderr)

            if stroke_versions:
                print(f"\\n[COMPLETE] 多stroke版本生成完成，成功: {len(stroke_versions)}/{len(valid_widths)}", flush=True, file=sys.stderr)
                return True, {
                    'original_path': restored_filename,
                    'stroke_versions': stroke_versions,
                    'generated_count': len(stroke_versions),
                    'total_requested': len(valid_widths)
                }
            else:
                return False, "所有stroke版本生成失败"

        except Exception as e:
            print(f"[ERROR] 多stroke版本生成失败: {e}", flush=True, file=sys.stderr)
            print(traceback.format_exc(), flush=True, file=sys.stderr)
            return False, str(e)

    def _generate_single_stroke_version(self, template_id, stroke_width, source_psd_path):
        """生成单个stroke版本的inside PSD

        Args:
            template_id (str): 模板ID
            stroke_width (int): stroke宽度
            source_psd_path (Path): 原始inside PSD路径

        Returns:
            tuple: (success, result_path_or_error)
        """
        try:
            stroke_filename = f"{template_id}_stroke_{stroke_width}px.psd"
            stroke_psd_path = self.inside_stroke_v2_dir / stroke_filename

            # 使用临时目录确保自动清理
            with tempfile.TemporaryDirectory(prefix=f"stroke_{stroke_width}px_") as temp_base:
                layers_dir = Path(temp_base) / "extracted"
                expanded_dir = Path(temp_base) / "expanded"
                stroked_dir = Path(temp_base) / "stroked"

                # 步骤1: 提取PNG图层
                print(f"  [STEP1] 提取PNG图层...", flush=True, file=sys.stderr)
                scaler = PSDScaler()
                extract_success = scaler.extract_layers_from_psd(str(source_psd_path), str(layers_dir))

                if not extract_success:
                    return False, f"PNG图层提取失败"

                # 步骤2: 画布外扩（中心锚点）：为每个PNG四面各扩 {stroke_width}px
                print(f"  [STEP2] 画布外扩 (四面各 {stroke_width}px)...", flush=True, file=sys.stderr)
                expanded_dir.mkdir(exist_ok=True)
                src_pngs = glob.glob(str(layers_dir / "*.png"))
                for p in src_pngs:
                    im = Image.open(p).convert('RGBA')
                    w, h = im.size
                    new_w, new_h = w + 2*int(stroke_width), h + 2*int(stroke_width)
                    canvas = Image.new('RGBA', (new_w, new_h), (0, 0, 0, 0))
                    canvas.paste(im, (int(stroke_width), int(stroke_width)))
                    dst = Path(expanded_dir) / Path(p).name
                    canvas.save(str(dst), 'PNG', optimize=True)

                # 步骤3: 对part图层进行描边处理（基于扩展后的PNG）
                print(f"  [STEP3] 描边part图层 (宽度: {stroke_width}px)...", flush=True, file=sys.stderr)
                stroked_dir.mkdir(exist_ok=True)

                # 创建描边处理器
                processor = PNGStrokeProcessor(
                    stroke_width=stroke_width,
                    stroke_color=(255, 255, 255, 255),
                    smooth_factor=1.0
                )

                # 处理每个图层
                png_files = glob.glob(str(expanded_dir / "*.png"))
                part_count = 0

                for png_file in png_files:
                    png_path = Path(png_file)
                    layer_name = png_path.stem
                    output_path = stroked_dir / png_path.name

                    if layer_name.startswith('part'):
                        # part图层进行描边
                        try:
                            result_image = processor.process_png(png_file)
                            result_image.save(str(output_path), 'PNG', optimize=True)
                            part_count += 1
                            print(f"    ✓ 描边完成: {layer_name}", flush=True, file=sys.stderr)
                        except Exception as e:
                            print(f"    ❌ 描边失败 {layer_name}: {e}", flush=True, file=sys.stderr)
                            return False, f"图层描边失败: {layer_name}"
                    else:
                        # 非part图层（含view）直接复制扩展后的PNG
                        shutil.copy2(png_file, output_path)
                        print(f"    ✓ 复制图层: {layer_name}", flush=True, file=sys.stderr)

                print(f"  [STEP3] 描边处理完成，part图层数: {part_count}", flush=True, file=sys.stderr)

                # 步骤4: 重组为PSD
                print(f"  [STEP4] 重组PSD...", flush=True, file=sys.stderr)
                create_success = scaler.create_psd_from_dir(str(stroked_dir), str(stroke_psd_path))

                if not create_success:
                    return False, f"PSD重组失败"

                print(f"  [SUCCESS] stroke版本生成完成: {stroke_filename}", flush=True, file=sys.stderr)
                return True, stroke_filename

        except Exception as e:
            print(f"  [ERROR] 单个stroke版本生成失败: {e}", flush=True, file=sys.stderr)
            print(traceback.format_exc(), flush=True, file=sys.stderr)
            return False, str(e)

    def _trim_transparent_edges(self, psd_path):
        """对PSD文件进行透明边缘裁剪"""
        try:
            # 打开PSD文件
            psd = PSDImage.open(psd_path)
            
            # 合成完整图像
            composite_image = psd.composite()
            
            # 转换为RGBA模式确保有透明通道
            if composite_image.mode != 'RGBA':
                composite_image = composite_image.convert('RGBA')
            
            # 获取图像边界框，去除透明边缘
            bbox = composite_image.getbbox()
            
            if bbox is None:
                # 如果整个图像都是透明的，跳过处理
                print("  Warning: image fully transparent, skipping trim")
                return
            
            # 获取裁剪后的尺寸
            left, top, right, bottom = bbox
            new_width = right - left
            new_height = bottom - top
            
            print(f"  Trim前尺寸: {psd.width}×{psd.height}", flush=True, file=sys.stderr)
            print(f"  Trim边界: left={left}, top={top}, right={right}, bottom={bottom}", flush=True, file=sys.stderr)
            print(f"  Trim后尺寸: {new_width}×{new_height}", flush=True, file=sys.stderr)
            
            # 如果没有需要裁剪的边缘，直接返回
            if left == 0 and top == 0 and right == psd.width and bottom == psd.height:
                print("  无需裁剪，图像已经是最小边界")
                return
            
            # 创建裁剪后的PSD
            self._create_trimmed_psd(psd_path, bbox)
            
        except Exception as e:
            print(f"  Trim透明边缘失败: {e}")
            print(f"  Trim错误详情: {traceback.format_exc()}")
            # 不抛出异常，因为这不是关键功能
    
    def _create_trimmed_psd(self, psd_path, bbox):
        """创建裁剪后的PSD文件"""
        try:
            original_psd_image = PSDImage.open(psd_path)
            
            left, top, right, bottom = bbox
            new_width = right - left
            new_height = bottom - top
            
            # 裁剪合成图像作为最终结果
            composite = original_psd_image.composite()
            cropped_composite = composite.crop(bbox)
            
            # 创建新的PSD文件，只包含裁剪后的图像
            self._save_cropped_psd(cropped_composite, psd_path, new_width, new_height)
                
            print(f"  Trim完成，新尺寸: {new_width}×{new_height}", flush=True, file=sys.stderr)
            
            # 验证保存结果
            try:
                test_psd = PSDImage.open(psd_path)
                print(f"  验证保存结果: {test_psd.width}×{test_psd.height}", flush=True, file=sys.stderr)
            except Exception as ve:
                print(f"  验证失败: {ve}", flush=True, file=sys.stderr)
            
        except Exception as e:
            print(f"  创建裁剪PSD失败: {e}", flush=True, file=sys.stderr)
            print(f"  裁剪错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)

    def _save_cropped_psd(self, cropped_image, psd_path, width, height):
        """保存裁剪后的图像为PSD格式"""
        try:
            
            # 将裁剪后的图像转换为RGBA
            if cropped_image.mode != 'RGBA':
                cropped_image = cropped_image.convert('RGBA')
                
            # 创建基本的PSD文件结构
            psd_data = self._create_basic_psd(cropped_image, width, height)
            
            # 写入文件
            with open(psd_path, 'wb') as f:
                f.write(psd_data)
                
            print(f"  成功保存裁剪PSD: {width}×{height}", flush=True, file=sys.stderr)
            
        except Exception as e:
            print(f"  保存裁剪PSD失败: {e}", flush=True, file=sys.stderr)
            # 降级方案：保存为PNG但扩展名保持.psd
            cropped_image.save(str(psd_path), 'PNG')

    def _create_basic_psd(self, image, width, height):
        """创建基本的PSD文件结构"""
        try:
            # 这是一个简化的PSD文件创建
            # 实际的PSD格式非常复杂，这里只创建最基本的结构
            
            # 获取图像数据
            image_data = image.tobytes()
            
            # PSD文件头
            header = b'8BPS'  # 签名
            header += struct.pack('>H', 1)  # 版本
            header += b'\x00' * 6  # 保留字段
            header += struct.pack('>H', 4)  # 通道数 (RGBA)
            header += struct.pack('>I', height)  # 高度
            header += struct.pack('>I', width)   # 宽度
            header += struct.pack('>H', 8)   # 位深度
            header += struct.pack('>H', 3)   # 颜色模式 (RGB)
            
            # 颜色模式数据段
            color_mode_data = struct.pack('>I', 0)  # 长度为0
            
            # 图像资源段
            image_resources = struct.pack('>I', 0)  # 长度为0
            
            # 图层和遮罩信息段
            layer_mask_info = struct.pack('>I', 0)  # 长度为0
            
            # 图像数据段
            image_data_length = len(image_data)
            compression = struct.pack('>H', 0)  # 无压缩
            
            # 构建最终的PSD数据
            psd_data = (header + 
                       color_mode_data + 
                       image_resources + 
                       layer_mask_info + 
                       compression + 
                       image_data)
            
            return psd_data
            
        except Exception as e:
            print(f"  创建PSD结构失败: {e}", flush=True, file=sys.stderr)
            raise

    def _render_reference_from_psd(self, psd_path, out_filename):
        """通用参考图渲染：基于给定PSD，将part图层白填充+黑边，以50%透明叠加输出PNG。

        与“stroke参考图”保持一致逻辑，唯一差异在于传入的PSD路径（原始inside或stroke版inside）。
        """
        try:
            psd = PSDImage.open(psd_path)
            canvas_width, canvas_height = psd.width, psd.height

            # 目标画布
            reference_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

            for layer in psd:
                layer_name = sanitize_name(layer.name).lower()
                if layer_name.startswith('part') and layer_name[4:].isdigit():
                    try:
                        layer_img = layer.topil().convert('RGBA')

                        # 放置到正确位置
                        layer_canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                        paste_x = max(0, layer.left)
                        paste_y = max(0, layer.top)
                        if paste_x < canvas_width and paste_y < canvas_height:
                            layer_canvas.paste(layer_img, (paste_x, paste_y), layer_img)

                        # 基于alpha生成黑边 + 白填充
                        _, _, _, canvas_alpha = layer_canvas.split()
                        dilated_alpha = canvas_alpha.filter(ImageFilter.MaxFilter(11))

                        layer_effect = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

                        # 黑边（50%）
                        la = layer_effect.load()
                        da = dilated_alpha.load()
                        ca = canvas_alpha.load()
                        for y in range(canvas_height):
                            for x in range(canvas_width):
                                if da[x, y] > 0:
                                    la[x, y] = (0, 0, 0, 128)
                        # 白填充（50%），覆盖黑边
                        for y in range(canvas_height):
                            for x in range(canvas_width):
                                if ca[x, y] > 0:
                                    la[x, y] = (255, 255, 255, 128)

                        reference_img = Image.alpha_composite(reference_img, layer_effect)
                    except Exception as layer_error:
                        print(f"Error processing layer: {layer_error}")
                        continue

            out_path = self.references_dir / out_filename
            reference_img.save(out_path, 'PNG')
            return True, out_filename
        except Exception as e:
            return False, str(e)

    def _generate_reference_image(self, inside_psd_path, template_id):
        """生成原始参考图：基于 restored.psd 渲染通用参考图。"""
        ok, res = self._render_reference_from_psd(inside_psd_path, f"{template_id}_reference.png")
        if ok:
            print(f"生成编辑参考图成功: {res}")
        else:
            print(f"生成编辑参考图失败: {res}")
        return ok, res

    def _generate_stroke_reference_image(self, template_id, stroke_width):
        """生成 stroke 参考图：逻辑与原参考图一致，但输入为 stroke 版 inside PSD。"""
        try:
            stroke_psd = self.inside_stroke_v2_dir / f"{template_id}_stroke_{int(stroke_width)}px.psd"
            if not stroke_psd.exists():
                return False, f"找不到stroke PSD: {stroke_psd.name}"
            return self._render_reference_from_psd(stroke_psd, f"{template_id}_stroke_{int(stroke_width)}px_reference.png")
        except Exception as e:
            return False, f"生成stroke参考图失败: {e}"

    def get_or_create_stroke_reference(self, template_id, stroke_width):
        """获取或按需生成 stroke 参考预览，并更新索引映射。"""
        # 先查现有索引
        templates = self._load_templates_index()
        record = next((t for t in templates if t.get('id') == template_id), None)
        mapping = {}
        if record:
            mapping = record.get('strokeReferences') or {}
            filename = mapping.get(str(stroke_width)) or mapping.get(int(stroke_width))
            if filename:
                candidate = self.references_dir / filename
                if candidate.exists():
                    return True, filename
        # 没有则生成：若缺失stroke版PSD，先按需生成
        stroke_psd = self.inside_stroke_v2_dir / f"{template_id}_stroke_{int(stroke_width)}px.psd"
        if not stroke_psd.exists():
            source_psd = self.get_restored_psd_path(template_id)
            if not source_psd or not source_psd.exists():
                return False, "restored PSD 不存在，无法生成stroke版本"
            ok_s, res_s = self._generate_single_stroke_version(template_id, int(stroke_width), source_psd)
            if not ok_s:
                return False, res_s

        ok, res = self._generate_stroke_reference_image(template_id, int(stroke_width))
        if not ok:
            return False, res

        # 更新索引
        def updater(t):
            refs = t.get('strokeReferences') or {}
            refs[str(int(stroke_width))] = res
            t['strokeReferences'] = refs
            # 兼容：也补一份数值key，方便老代码读取
            refs_numkey = {int(k): v for k, v in refs.items() if str(k).isdigit()}
            t['strokeReferences'] = {str(k): v for k, v in refs_numkey.items()}
            return t
        self._update_template_record(template_id, updater)
        return True, res
    
    def save_template(self, psd_path, original_filename, stroke_widths=None):
        """保存PSD模板到存储目录"""
        try:
            # 验证文件
            is_valid, result = self.validate_psd(psd_path)
            if not is_valid:
                return False, result
            
            # 处理重名文件
            unique_filename = self._get_unique_filename(original_filename)
            
            # 生成唯一ID
            template_id = f"tpl_{int(datetime.now().timestamp() * 1000)}"
            
            # 保存文件
            file_extension = Path(unique_filename).suffix
            saved_filename = f"{template_id}{file_extension}"
            saved_path = self.templates_dir / saved_filename
            
            shutil.copy2(psd_path, saved_path)
            
            
            # 生成预览参考图：part图层合并+50%灰色填充
            preview_success, preview_result = self._generate_preview_image(saved_path, template_id)
            preview_filename = preview_result if preview_success else None
            
            # 对原始PSD进行逆展开变换，生成b.psd
            restore_success, restore_result = self._generate_restored_psd(saved_path, template_id)
            restored_filename = restore_result if restore_success else None

            # 生成多stroke版本（如果配置了stroke宽度）
            stroke_versions = {}
            if restore_success and stroke_widths:
                stroke_success, stroke_result = self._generate_multi_stroke_versions(template_id, stroke_widths)
                if stroke_success:
                    stroke_versions = stroke_result.get('stroke_versions', {})
                    print(f"[STROKE] 成功生成 {len(stroke_versions)} 个stroke版本", flush=True, file=sys.stderr)
                else:
                    print(f"[STROKE] stroke版本生成失败: {stroke_result}", flush=True, file=sys.stderr)

            # 基于 restored.psd 生成 stroke 透明参考图（第二阶段）
            stroke_references = {}
            if restore_success and stroke_versions:
                for w in sorted(stroke_versions.keys(), key=lambda x: int(x)):
                    try:
                        ok, ref_name = self._generate_stroke_reference_image(template_id, int(w))
                        if ok:
                            stroke_references[int(w)] = ref_name
                            print(f"[STROKE] 参考图生成完成: {w}px -> {ref_name}", flush=True, file=sys.stderr)
                        else:
                            print(f"[STROKE] 参考图生成失败: {w}px -> {ref_name}", flush=True, file=sys.stderr)
                    except Exception as e:
                        print(f"[STROKE] 参考图生成异常: {w}px -> {e}", flush=True, file=sys.stderr)

            # 基于b.psd生成编辑参考图
            if restore_success:
                restored_path = self.inside_dir / restored_filename
                reference_success, reference_result = self._generate_reference_image(restored_path, template_id)
                reference_filename = reference_result if reference_success else None
            else:
                reference_success = False
                reference_filename = None
            
            # 获取文件信息
            psd_info = self.get_psd_info(saved_path)
            file_size = saved_path.stat().st_size
            
            # 创建模板记录
            template_record = {
                'id': template_id,
                'name': Path(unique_filename).stem,
                'fileName': unique_filename,
                'originalFileName': original_filename,
                'savedFileName': saved_filename,
                'restoredFileName': restored_filename,
                'previewImage': preview_filename,
                'referenceImage': reference_filename,
                'size': file_size,
                'uploadedAt': datetime.now().isoformat(),
                'status': 'ready',
                'dimensions': {
                    'width': psd_info['width'],
                    'height': psd_info['height']
                } if psd_info else None,
                'layers': psd_info['layers'] if psd_info else [],
                'viewLayer': psd_info['viewLayer'] if psd_info and psd_info.get('viewLayer') else None,
                'strokeVersions': stroke_versions,  # 添加stroke版本映射
                'strokeConfig': list(stroke_versions.keys()) if stroke_versions else [],  # 记录配置的stroke宽度
                'strokeReferences': {str(k): v for k, v in stroke_references.items()} if stroke_references else {},
                'components': []  # 初始化为空的部件列表
            }
            
            # 更新索引
            templates = self._load_templates_index()
            templates.insert(0, template_record)  # 新模板放在前面
            self._save_templates_index(templates)
            
            return True, template_record
            
        except Exception as e:
            return False, f"保存模板失败: {str(e)}"
    
    def get_templates(self):
        """获取所有模板"""
        return self._load_templates_index()
    
    def get_restored_psd_path(self, template_id):
        """获取模板的逆展开变换PSD文件路径（b.psd）"""
        template = self.get_template_by_id(template_id)
        if template and template.get('restoredFileName'):
            return self.inside_dir / template['restoredFileName']
        return None

    def get_template_by_id(self, template_id):
        """根据ID获取模板"""
        templates = self._load_templates_index()
        for template in templates:
            if template['id'] == template_id:
                return template
        return None
    
    def generate_final_psd(self, template_id, image_path, force_resize=False, component_id=None, stroke_width=None):
        """生成最终PSD文件的完整流程"""
        try:
            # 获取模板信息
            template = self.get_template_by_id(template_id)
            if not template:
                return False, "模板不存在"
            
            if not template.get('restoredFileName'):
                return False, "模板缺少变换结果文件"
            
            # 选择用于裁切的 inside PSD：原始或指定的 stroke 版本
            selected_psd_path = None
            used_stroke_width = None
            if stroke_width is not None and str(stroke_width) != "":
                try:
                    sw = int(stroke_width)
                except Exception:
                    return False, "无效的stroke宽度"

                # 仅允许使用已存在的 stroke 版本
                versions = template.get('strokeVersions') or {}
                # 兼容键类型（int/str）
                candidate_name = versions.get(sw) or versions.get(str(sw))
                if not candidate_name:
                    return False, "未配置该stroke版本"
                p = self.inside_stroke_v2_dir / candidate_name
                if not p.exists():
                    return False, "所选stroke版本文件不存在"
                selected_psd_path = p
                used_stroke_width = sw
            else:
                # 默认使用 restored.psd
                selected_psd_path = self.inside_dir / template['restoredFileName']
                if not selected_psd_path.exists():
                    return False, "变换结果文件不存在"
            
            # 生成唯一ID
            result_id = f"result_{int(datetime.now().timestamp() * 1000)}"
            if used_stroke_width is not None:
                result_id = f"{result_id}_stroke_{used_stroke_width}px"
            
            # 步骤0: 图片对齐预处理
            aligned_success, aligned_image_path, aligned_template_path = self._align_image_to_template(
                image_path, str(selected_psd_path), force_resize, result_id
            )
            
            if not aligned_success:
                return False, "图片对齐失败"
            
            # 步骤1: 使用内置psd_replacer进行裁切 aligned_template + aligned_image -> result.psd
            result_success, result_path = self._apply_psd_replacer(
                aligned_template_path, aligned_image_path, result_id
            )
            
            if not result_success:
                return False, f"PSD裁切失败: {result_path}"
            
            # 步骤2: 使用transform_template_final进行最终变换 result.psd -> final.psd
            final_success, final_path = self._apply_final_transform(
                result_path, result_id, used_stroke_width
            )
            
            if not final_success:
                # 清理result文件
                if os.path.exists(result_path):
                    os.unlink(result_path)
                return False, f"最终变换失败: {final_path}"
            
            # 步骤3: 如果选择了部件，添加window图层
            if component_id:
                # 严格验证部件是否存在
                component_path = self.get_component_file_path(template_id, component_id)
                if not component_path or not component_path.exists():
                    return False, f"选择的部件不存在: {component_id}"
                
                window_success, final_path = self._add_window_layer(
                    final_path, template_id, component_id, result_id
                )
                if not window_success:
                    return False, f"添加window图层失败: {final_path}"
            
            # 步骤4: 生成final.psd的预览图（在window叠加之后），并隐藏view图层
            preview_success, preview_path = self._generate_final_preview(
                final_path, result_id
            )

            # 步骤5: 如果预览图生成成功，添加到索引
            if preview_success:
                template_name = template.get('name', f'Template_{template_id}')
                index_success = self._add_to_results_index(result_id, template_id, template_name, used_stroke_width=used_stroke_width)
                if index_success:
                    print(f"索引记录已添加: {result_id}")
                else:
                    print(f"索引记录添加失败: {result_id}")

            # 准备返回数据
            result_data = {
                'resultId': result_id,
                'templateId': template_id,
                'finalPsdPath': final_path,
                'previewPath': preview_path if preview_success else None,
                'generatedAt': datetime.now().isoformat(),
                'template': template,
                'usedStrokeWidth': used_stroke_width
            }
            
            print(f"生成流程完成: {result_id}")

            # 清理临时文件
            self._cleanup_temp_files(result_id)

            return True, result_data

        except Exception as e:
            print(f"生成最终PSD失败: {e}")
            print(traceback.format_exc())

            # 出错时也要清理临时文件
            self._cleanup_temp_files(result_id)

            return False, str(e)
    
    def _apply_psd_replacer(self, template_psd_path, image_path, result_id):
        """使用内置PSD替换器进行图片替换"""
        try:
            print(f"开始PSD替换，模板: {template_psd_path}, 图片: {image_path}", flush=True, file=sys.stderr)
            
            # 检查输入文件是否存在
            if not os.path.exists(template_psd_path):
                print(f"模板PSD文件不存在: {template_psd_path}", flush=True, file=sys.stderr)
                return False, "模板PSD文件不存在"
            
            if not os.path.exists(image_path):
                print(f"输入图片文件不存在: {image_path}", flush=True, file=sys.stderr)
                return False, "输入图片文件不存在"
            
            result_filename = f"{result_id}_result.psd"
            result_path = self.temp_dir / result_filename
            print(f"输出文件路径: {result_path}", flush=True, file=sys.stderr)
            
            # 使用内置PSD替换器
            success = self._replace_psd_internal(template_psd_path, image_path, str(result_path))
            
            # 验证输出文件是否生成
            if result_path.exists():
                file_size = result_path.stat().st_size
                print(f"PSD替换成功: {result_filename}, 文件大小: {file_size} bytes", flush=True, file=sys.stderr)
                return True, str(result_path)
            else:
                print(f"PSD替换完成但文件未生成: {result_path}", flush=True, file=sys.stderr)
                return False, "替换结果文件未生成"
            
        except Exception as e:
            print(f"PSD替换失败: {e}", flush=True, file=sys.stderr)
            print(f"PSD替换错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return False, str(e)
    
    def _align_image_to_template(self, image_path, template_psd_path, force_resize=False, result_id: str = ""):
        """智能图片与模板尺寸对齐：比较尺寸决定调整方向
        
        Args:
            force_resize: 强制将图片调整到模板尺寸，无视面积大小
            result_id: 用于命名临时文件的结果ID，便于调试与避免冲突
        """
        
        print("📐 智能尺寸对齐开始", flush=True, file=sys.stderr)
        
        try:
            # 加载模板PSD
            print(f"  正在加载模板PSD: {template_psd_path}", flush=True, file=sys.stderr)
            template = PSDImage.open(template_psd_path)
            template_w, template_h = template.width, template.height
            template_area = template_w * template_h
            print(f"  模板尺寸: {template_w} × {template_h} (面积: {template_area})", flush=True, file=sys.stderr)
            
        except Exception as e:
            error_msg = f"加载模板PSD失败: {template_psd_path} - {str(e)}"
            print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
            raise Exception(error_msg)
        
        try:
            # 加载输入图片
            print(f"  正在加载输入图片: {image_path}", flush=True, file=sys.stderr)
            image = Image.open(image_path)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            image_w, image_h = image.size
            image_area = image_w * image_h
            print(f"  图片尺寸: {image_w} × {image_h} (面积: {image_area})", flush=True, file=sys.stderr)
            
        except Exception as e:
            error_msg = f"加载输入图片失败: {image_path} - {str(e)}"
            print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
            raise Exception(error_msg)
        
        # 检查是否需要调整
        if template_w == image_w and template_h == image_h:
            print("  ✓ 尺寸完全匹配，无需调整", flush=True, file=sys.stderr)
            return True, image_path, template_psd_path
        
        # 强制调整模式：无视面积大小，始终调整图片到模板尺寸
        if force_resize:
            print(f"  [TARGET] 强制对齐模式：调整用户图片: {image_w}×{image_h} -> {template_w}×{template_h}", flush=True, file=sys.stderr)
            
            try:
                # 调整图片尺寸
                # 使用带有步骤名的临时输出路径
                step_out = self.temp_dir / f"{result_id}_step1_aligned_image.png" if result_id else None
                resized_image_path = self._resize_image_to_template_size(image_path, template_w, template_h, str(step_out) if step_out else None)
                if not resized_image_path:
                    error_msg = f"_resize_image_to_template_size返回None"
                    print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                    raise Exception(error_msg)
                
                # 验证调整结果
                try:
                    adjusted_image = Image.open(resized_image_path)
                    actual_w, actual_h = adjusted_image.size
                    print(f"  [SUCCESS] 强制调整完成: {actual_w} × {actual_h}", flush=True, file=sys.stderr)
                    
                    if actual_w != template_w or actual_h != template_h:
                        error_msg = f"强制调整后尺寸不匹配: 期望{template_w}×{template_h}, 实际{actual_w}×{actual_h}"
                        print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                        raise Exception(error_msg)
                        
                except Exception as e:
                    error_msg = f"验证强制调整后图片失败: {str(e)}"
                    print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                    raise Exception(error_msg)
                
                return True, resized_image_path, template_psd_path
                
            except Exception as e:
                error_msg = f"强制调整图片尺寸过程失败: {str(e)}"
                print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                raise Exception(error_msg)
        
        # 非强制模式：统一调整模板PSD到用户图片尺寸（不改动用户图片）
        print(f"  [PROCESS] 非强制模式：调整模板PSD以匹配图片: {template_w}×{template_h} -> {image_w}×{image_h}", flush=True, file=sys.stderr)
        try:
            temp_psd_path = str(self.temp_dir / f"{result_id}_step1_aligned_template.psd") if result_id else None
            if not temp_psd_path:
                with tempfile.NamedTemporaryFile(suffix='.psd', delete=False) as temp_psd:
                    temp_psd_path = temp_psd.name
            print(f"  创建临时PSD文件: {temp_psd_path}", flush=True, file=sys.stderr)
            success = self._full_scale_psd_internal(template_psd_path, image_w, image_h, temp_psd_path)
            if not success:
                error_msg = f"调用_full_scale_psd_internal失败"
                print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                raise Exception(error_msg)

            # 验证调整结果
            try:
                adjusted_template = PSDImage.open(temp_psd_path)
                actual_w, actual_h = adjusted_template.width, adjusted_template.height
                print(f"  [SUCCESS] 模板调整完成: {actual_w} × {actual_h}", flush=True, file=sys.stderr)
                if actual_w != image_w or actual_h != image_h:
                    error_msg = f"模板调整后尺寸不匹配: 期望{image_w}×{image_h}, 实际{actual_w}×{actual_h}"
                    print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                    raise Exception(error_msg)
            except Exception as e:
                error_msg = f"验证调整后模板失败: {str(e)}"
                print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
                raise Exception(error_msg)

            return True, image_path, temp_psd_path

        except Exception as e:
            error_msg = f"调整模板PSD尺寸过程失败: {str(e)}"
            print(f"[ERROR] {error_msg}", flush=True, file=sys.stderr)
            raise Exception(error_msg)

    def _resize_psd_with_internal_module(self, template_psd_path, target_width, target_height):
        """使用内部PSD调整模块生成调整尺寸的PSD文件"""
        try:
            
            print(f"  [CONFIG] 调用内部PSD调整器: {target_width} × {target_height}", flush=True, file=sys.stderr)
            
            # 创建临时输出文件
            with tempfile.NamedTemporaryFile(suffix='.psd', delete=False) as temp_file:
                temp_output_path = temp_file.name
            
            # 使用内部PSDResizerV2模块
            resizer = PSDResizerV2(
                input_path=template_psd_path,
                target_width=target_width,
                target_height=target_height,
                output_path=temp_output_path
            )
            
            # 执行调整
            success = resizer.resize_psd()
            
            if not success:
                print(f"  [ERROR] PSD调整失败", flush=True, file=sys.stderr)
                return None
            
            # 检查输出文件是否存在
            if not os.path.exists(temp_output_path):
                print(f"  [ERROR] 输出文件未生成: {temp_output_path}", flush=True, file=sys.stderr)
                return None
                
            file_size = os.path.getsize(temp_output_path)
            if file_size == 0:
                print(f"  [ERROR] 输出文件为空", flush=True, file=sys.stderr)
                return None
            
            print(f"  [SUCCESS] PSD调整完成, 文件大小: {file_size} bytes", flush=True, file=sys.stderr)
            
            # 验证生成的PSD文件
            try:
                test_psd = PSDImage.open(temp_output_path)
                print(f"  [SUCCESS] 验证成功: {test_psd.width}×{test_psd.height}, 图层数: {len(list(test_psd))}", flush=True, file=sys.stderr)

                # 检查part图层
                part_layers = []
                for layer in test_psd:
                    lname = sanitize_name(layer.name).lower()
                    if lname in ['part1', 'part2', 'part3', 'part4']:
                        part_layers.append(lname)
                print(f"  [SUCCESS] 发现part图层: {part_layers}", flush=True, file=sys.stderr)

            except Exception as ve:
                print(f"  [WARNING] 验证PSD时出现警告: {ve}", flush=True, file=sys.stderr)
                # 不阻止流程，因为可能只是psd-tools的兼容性问题
            
            return temp_output_path
            
        except Exception as e:
            print(f"  [ERROR] PSD调整失败: {e}", flush=True, file=sys.stderr)
            print(f"  错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return None

    def _create_resized_psd(self, template_psd, target_width, target_height):
        """创建调整尺寸后的真实PSD文件，保留完整图层结构"""
        try:
                
            print(f"  [CONFIG] 生成调整尺寸的PSD: {target_width} × {target_height}", flush=True, file=sys.stderr)
            
            # 计算缩放比例
            scale_x = target_width / template_psd.width
            scale_y = target_height / template_psd.height
            print(f"  缩放比例: X={scale_x:.3f}, Y={scale_y:.3f}", flush=True, file=sys.stderr)
            
            # 收集所有调整后的图层数据
            resized_layers = []
            part_layer_count = 0
            
            for layer in template_psd:
                try:
                    layer_img = layer.composite()
                    if layer_img:
                        # 获取图层原始位置和尺寸
                        x1, y1 = layer.left, layer.top
                        x2, y2 = layer.right, layer.bottom
                        
                        # 应用缩放到位置和尺寸
                        new_x1 = int(x1 * scale_x)
                        new_y1 = int(y1 * scale_y)
                        new_width = int((x2 - x1) * scale_x)
                        new_height = int((y2 - y1) * scale_y)
                        
                        if new_width > 0 and new_height > 0:
                            # 缩放图层图像
                            resized_layer = layer_img.resize((new_width, new_height), Image.LANCZOS)
                            
                            # 保存图层信息
                            resized_layers.append({
                            'name': sanitize_name(layer.name),
                            'image': resized_layer,
                            'position': (new_x1, new_y1),
                            'visible': layer.visible
                        })
                            
                            # 统计part图层
                            if layer.name.lower() in ['part1', 'part2', 'part3', 'part4']:
                                part_layer_count += 1
                            
                            print(f"    处理图层: {layer.name} -> {new_width}x{new_height} at ({new_x1},{new_y1})", flush=True, file=sys.stderr)
                
                except Exception as layer_error:
                    print(f"    跳过图层 {layer.name}: {layer_error}", flush=True, file=sys.stderr)
                    continue
            
            print(f"  ✓ 成功处理 {len(resized_layers)} 个图层，包含 {part_layer_count} 个part图层", flush=True, file=sys.stderr)
            
            # 生成保留图层结构的真实PSD文件
            with tempfile.NamedTemporaryFile(suffix='.psd', delete=False) as temp_file:
                # 创建带图层的PSD数据
                psd_data = self._create_layered_psd_data(resized_layers, target_width, target_height)
                temp_file.write(psd_data)
                temp_psd_path = temp_file.name
            
            # 验证生成的PSD文件
                test_psd = PSDImage.open(temp_psd_path)
            print(f"  [SUCCESS] 验证PSD文件: {test_psd.width}×{test_psd.height}, 图层数: {len(list(test_psd))}", flush=True, file=sys.stderr)
            
            # 验证part图层是否存在
            part_layers_found = []
            for layer in test_psd:
                lname = sanitize_name(layer.name).lower()
                if lname in ['part1', 'part2', 'part3', 'part4']:
                    part_layers_found.append(lname)
            print(f"  [SUCCESS] 发现part图层: {part_layers_found}", flush=True, file=sys.stderr)
            
            return temp_psd_path
            
        except Exception as e:
            print(f"  [ERROR] 生成调整尺寸PSD失败: {e}", flush=True, file=sys.stderr)
            print(f"  错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return None

    def _create_real_psd_data(self, canvas_image, width, height):
        """创建真实的PSD文件二进制数据"""
        
        # 确保图像是RGBA模式
        if canvas_image.mode != 'RGBA':
            canvas_image = canvas_image.convert('RGBA')
        
        # 获取图像数据
        image_data = list(canvas_image.getdata())
        
        # 创建PSD数据流
        psd_data = io.BytesIO()
        
        # PSD文件签名
        psd_data.write(b'8BPS')
        
        # 版本号 (1)
        psd_data.write(struct.pack('>H', 1))
        
        # 保留字段 (6 bytes)
        psd_data.write(b'\x00' * 6)
        
        # 通道数 (4 = RGBA)
        psd_data.write(struct.pack('>H', 4))
        
        # 高度和宽度
        psd_data.write(struct.pack('>I', height))
        psd_data.write(struct.pack('>I', width))
        
        # 每通道位深 (8)
        psd_data.write(struct.pack('>H', 8))
        
        # 色彩模式 (3 = RGB)
        psd_data.write(struct.pack('>H', 3))
        
        # 色彩模式数据长度 (0)
        psd_data.write(struct.pack('>I', 0))
        
        # 图像资源长度 (0)
        psd_data.write(struct.pack('>I', 0))
        
        # 图层信息长度 (0 - 扁平化图像)
        psd_data.write(struct.pack('>I', 0))
        
        # 图像数据
        # 压缩方式 (0 = 无压缩)
        psd_data.write(struct.pack('>H', 0))
        
        # 按通道写入图像数据
        for channel in range(4):  # RGBA
            for pixel in image_data:
                psd_data.write(struct.pack('B', pixel[channel]))
        
        return psd_data.getvalue()

    def _create_layered_psd_data(self, layers, width, height):
        """创建带完整图层结构的PSD文件二进制数据"""
        
        print(f"    创建带图层的PSD数据: {width}×{height}, 图层数: {len(layers)}", flush=True, file=sys.stderr)
        
        # 创建PSD数据流
        psd_data = io.BytesIO()
        
        # PSD文件头
        psd_data.write(b'8BPS')              # 签名
        psd_data.write(struct.pack('>H', 1)) # 版本
        psd_data.write(b'\x00' * 6)          # 保留字段
        psd_data.write(struct.pack('>H', 4)) # 通道数 (RGBA)
        psd_data.write(struct.pack('>I', height))  # 高度
        psd_data.write(struct.pack('>I', width))   # 宽度
        psd_data.write(struct.pack('>H', 8))       # 位深
        psd_data.write(struct.pack('>H', 3))       # 色彩模式 (RGB)
        
        # 色彩模式数据段（空）
        psd_data.write(struct.pack('>I', 0))
        
        # 图像资源段（空）
        psd_data.write(struct.pack('>I', 0))
        
        # 图层和蒙版信息段（我们先构建到内存，再一次性写入主流，并填入总长度）
        # 1) 图层信息段 layer_section
        layer_section = io.BytesIO()
        
        # 图层计数（负数表示有alpha通道）
        layer_section.write(struct.pack('>h', -len(layers)))
        
        # 写入每个图层的记录
        for layer in layers:
            img = layer['image']
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            x, y = layer['position']
            w, h = img.size
            
            # 确保位置和尺寸在有效范围内
            x = max(0, min(x, width))
            y = max(0, min(y, height))
            w = min(w, width - x) if x < width else 1
            h = min(h, height - y) if y < height else 1
            
            # 图层边界
            layer_section.write(struct.pack('>I', y))         # top
            layer_section.write(struct.pack('>I', x))         # left  
            layer_section.write(struct.pack('>I', y + h))     # bottom
            layer_section.write(struct.pack('>I', x + w))     # right
            
            # 通道信息 (RGBA = 4个通道)
            layer_section.write(struct.pack('>H', 4))         # 通道数
            channel_size = w * h + 2  # 数据大小 + 压缩标记
            
            # Alpha通道 (ID = -1)
            layer_section.write(struct.pack('>h', -1))
            layer_section.write(struct.pack('>I', channel_size))
            
            # RGB通道 (ID = 0,1,2)
            for i in range(3):
                layer_section.write(struct.pack('>h', i))
                layer_section.write(struct.pack('>I', channel_size))
            
            # 混合模式签名
            layer_section.write(b'8BIM')
            layer_section.write(b'norm')  # 正常混合模式
            layer_section.write(struct.pack('B', 255))  # 不透明度
            layer_section.write(struct.pack('B', 0))    # 剪切
            layer_section.write(struct.pack('B', 1 if layer.get('visible', True) else 0))  # 可见性
            layer_section.write(struct.pack('B', 0))    # 填充
            
            # 额外数据长度
            extra_data_length_pos = layer_section.tell()
            layer_section.write(struct.pack('>I', 0))  # 占位符
            
            extra_start = layer_section.tell()
            
            # 图层蒙版数据（空）
            layer_section.write(struct.pack('>I', 0))
            
            # 图层混合范围（空）
            layer_section.write(struct.pack('>I', 0))
            
            # 图层名称
            layer_name = layer['name'].encode('utf-8')
            name_length = len(layer_name)
            padded_length = (name_length + 4) & ~3  # 4字节对齐
            layer_section.write(struct.pack('B', name_length))
            layer_section.write(layer_name)
            layer_section.write(b'\x00' * (padded_length - name_length - 1))
            
            # 填充额外数据长度
            extra_end = layer_section.tell()
            extra_length = extra_end - extra_start
            layer_section.seek(extra_data_length_pos)
            layer_section.write(struct.pack('>I', extra_length))
            layer_section.seek(extra_end)
        
        # 写入图层图像数据
        for layer in layers:
            img = layer['image']
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            x, y = layer['position']
            w, h = img.size
            
            # 确保尺寸有效
            w = min(w, width - x) if x < width else 1
            h = min(h, height - y) if y < height else 1
            
            if w > 0 and h > 0:
                # 裁剪图像到有效尺寸
                if img.size != (w, h):
                    img = img.crop((0, 0, w, h))
                
                pixels = list(img.getdata())
                
                # 为每个通道写入数据 (Alpha, R, G, B)
                for channel in [3, 0, 1, 2]:  # A, R, G, B
                    layer_section.write(struct.pack('>H', 0))  # 无压缩
                    for pixel in pixels:
                        layer_section.write(struct.pack('B', pixel[channel]))
        
        # 2) 组装 Layer and Mask 信息块
        layer_data = layer_section.getvalue()
        lam = io.BytesIO()
        # 图层信息长度 + 数据
        lam.write(struct.pack('>I', len(layer_data)))
        lam.write(layer_data)
        # 全局蒙版信息（空）
        lam.write(struct.pack('>I', 0))
        lam_bytes = lam.getvalue()

        # 3) 写入 Layer and Mask 总长度占位/填充
        layer_and_mask_length = len(lam_bytes)
        psd_data.write(struct.pack('>I', layer_and_mask_length))
        psd_data.write(lam_bytes)
        
        # 合成图像数据（创建空白图像）
        psd_data.write(struct.pack('>H', 0))  # 无压缩
        
        # 写入空白的合成图像数据
        total_pixels = width * height
        for channel in range(4):  # RGBA
            for _ in range(total_pixels):
                psd_data.write(struct.pack('B', 0))
        
        print(f"    ✓ PSD数据生成完成，总大小: {psd_data.tell()} 字节", flush=True, file=sys.stderr)
        
        return psd_data.getvalue()

    def _replace_psd_internal(self, template_psd_path, image_path, output_path):
        """使用原始PSD替换逻辑"""
        try:
            print("=" * 60, flush=True, file=sys.stderr)
            print("[TARGET] 使用原始PSD替换逻辑", flush=True, file=sys.stderr)
            print(f"  模板: {template_psd_path}", flush=True, file=sys.stderr)
            print(f"  图片: {image_path}", flush=True, file=sys.stderr)
            print(f"  输出: {output_path}", flush=True, file=sys.stderr)
            print("=" * 60, flush=True, file=sys.stderr)
            
            # 创建原始PSD替换器（不传递任何缩放因子）
            replacer = PSDReplacer()
            success = replacer.replace(template_psd_path, image_path, output_path)

            if not success:
                return False
                
            print("[SUCCESS] PSD替换完成", flush=True, file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"[ERROR] PSD替换失败: {e}", flush=True, file=sys.stderr)
            print(f"[ERROR] 错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return False

    def _resize_image_to_template_size(self, image_path, template_width, template_height, output_path=None):
        """强制将图片调整到目标尺寸（不保持比例）。
        如果提供 output_path，则写入该路径，否则创建临时文件返回路径。
        """
        try:
                
            print(f"  [CONFIG] 强制调整图片尺寸: -> {template_width}×{template_height}", flush=True, file=sys.stderr)
            
            # 加载图片
            image = Image.open(image_path)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            original_size = image.size
            print(f"     原尺寸: {original_size[0]}×{original_size[1]}", flush=True, file=sys.stderr)
            
            # 强制调整到目标尺寸（不保持比例）
            resized_image = image.resize((template_width, template_height), Image.LANCZOS)
            print(f"     新尺寸: {template_width}×{template_height} ✓", flush=True, file=sys.stderr)
            
            # 保存到指定输出或临时文件
            if output_path:
                # 确保目录存在
                out_dir = os.path.dirname(output_path)
                os.makedirs(out_dir, exist_ok=True)
                resized_image.save(output_path)
                print(f"     保存到: {output_path}", flush=True, file=sys.stderr)
                return output_path
            else:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    resized_image.save(temp_file.name)
                    print(f"     保存到: {temp_file.name}", flush=True, file=sys.stderr)
                    return temp_file.name
        
        except Exception as e:
            print(f"[ERROR] 调整图片尺寸失败: {e}", flush=True, file=sys.stderr)
            return None

    def _full_scale_psd_internal(self, psd_path, width, height, output_path):
        """完整的PSD缩放流程，使用内部PSD缩放模块"""
        try:
            
            print(f"[START] 内部PSD缩放开始:", flush=True, file=sys.stderr)
            print(f"   输入: {psd_path}", flush=True, file=sys.stderr)
            print(f"   输出: {output_path}", flush=True, file=sys.stderr)
            print(f"   目标尺寸: {width}×{height}", flush=True, file=sys.stderr)
            
            # 创建PSD缩放器
            scaler = PSDScaler()
            
            # 执行缩放
            success = scaler.scale_psd(psd_path, output_path, width, height)
            
            if success:
                print(f"[SUCCESS] PSD缩放成功: {output_path}", flush=True, file=sys.stderr)
                
                # 验证输出文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   文件大小: {file_size} bytes", flush=True, file=sys.stderr)
                    return True
                else:
                    print(f"[ERROR] 输出文件不存在: {output_path}", flush=True, file=sys.stderr)
                    return False
            else:
                print(f"[ERROR] PSD缩放失败", flush=True, file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"[ERROR] PSD缩放异常: {e}", flush=True, file=sys.stderr)
            print(f"[ERROR] 详细错误: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return False





    def _create_scaled_psd(self, template_psd_path, target_width, target_height):
        """生成缩放后的PSD文件"""
        try:
                    
            print(f"  [DOCUMENT] 生成缩放PSD: {target_width} × {target_height}", flush=True, file=sys.stderr)
            
            # 加载原始PSD
            template = PSDImage.open(template_psd_path)
            orig_w, orig_h = template.width, template.height
            
            # 计算缩放比例
            scale_x = target_width / orig_w
            scale_y = target_height / orig_h
            
            print(f"    原始尺寸: {orig_w} × {orig_h}", flush=True, file=sys.stderr)
            print(f"    缩放比例: x={scale_x:.3f}, y={scale_y:.3f}", flush=True, file=sys.stderr)
            
            # 创建缩放后的画布
            scaled_canvas = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 0))
            
            # 遍历并缩放所有图层
            for layer in template:
                try:
                    if hasattr(layer, 'bbox') and layer.bbox:
                        # 获取图层图像
                        layer_img = layer.topil()
                        if layer_img.mode != 'RGBA':
                            layer_img = layer_img.convert('RGBA')
                        
                        # 计算缩放后的位置和尺寸
                        x1, y1, x2, y2 = layer.bbox
                        new_x1 = int(x1 * scale_x)
                        new_y1 = int(y1 * scale_y)
                        new_x2 = int(x2 * scale_x)
                        new_y2 = int(y2 * scale_y)
                        
                        new_width = new_x2 - new_x1
                        new_height = new_y2 - new_y1
                        
                        if new_width > 0 and new_height > 0:
                            # 缩放图层图像
                            scaled_layer_img = layer_img.resize((new_width, new_height), Image.LANCZOS)
                            
                            # 粘贴到画布
                            scaled_canvas.paste(scaled_layer_img, (new_x1, new_y1), scaled_layer_img)
                        
                except Exception as layer_e:
                    print(f"    警告: 处理图层 {layer.name} 失败: {layer_e}", flush=True, file=sys.stderr)
                    continue
            
            # 保存为临时PSD文件（以PNG格式）
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                scaled_canvas.save(temp_file.name, 'PNG')
                scaled_psd_path = temp_file.name
            
            print(f"    ✓ 缩放PSD已生成: {scaled_psd_path}", flush=True, file=sys.stderr)
            return scaled_psd_path
            
        except Exception as e:
            print(f"[ERROR] 生成缩放PSD失败: {e}", flush=True, file=sys.stderr)
            return None
    
    def _apply_final_transform(self, result_psd_path, result_id, stroke_width=None):
        """应用最终变换"""
        try:
            print(f"开始最终变换，输入文件: {result_psd_path}", flush=True, file=sys.stderr)
            
            # 检查输入文件是否存在
            if not os.path.exists(result_psd_path):
                print(f"输入PSD文件不存在: {result_psd_path}", flush=True, file=sys.stderr)
                return False, "输入PSD文件不存在"
            
            final_filename = f"{result_id}_final.psd"
            final_path = self.result_downloads_dir / final_filename
            print(f"输出文件路径: {final_path}", flush=True, file=sys.stderr)
            
            # 使用transform_template_final进行最终变换
            transformer = BinaryPSDTransformer(result_psd_path, str(final_path), stroke_width)
            transformer.transform()
            
            # 验证输出文件是否生成成功
            if final_path.exists():
                file_size = final_path.stat().st_size
                print(f"最终变换成功: {final_filename}, 文件大小: {file_size} bytes", flush=True, file=sys.stderr)
                return True, str(final_path)
            else:
                print(f"最终变换完成但文件未生成: {final_path}", flush=True, file=sys.stderr)
                return False, "输出文件未生成"
            
        except Exception as e:
            print(f"最终变换失败: {e}", flush=True, file=sys.stderr)
            print(f"最终变换错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return False, str(e)
    
    def _generate_final_preview(self, final_psd_path, result_id):
        """生成最终PSD的预览图"""
        try:
            print(f"开始生成最终预览图，PSD路径: {final_psd_path}", flush=True, file=sys.stderr)
            
            preview_filename = f"{result_id}_final_preview.png"
            preview_path = self.result_previews_dir / preview_filename
            
            # 检查PSD文件是否存在
            if not Path(final_psd_path).exists():
                print(f"PSD文件不存在: {final_psd_path}", flush=True, file=sys.stderr)
                return False, "PSD文件不存在"
            
            # 使用psd_tools生成预览图，并隐藏view图层
            print(f"正在打开PSD文件...", flush=True, file=sys.stderr)
            psd = PSDImage.open(final_psd_path)
            print(f"PSD尺寸: {psd.width}×{psd.height}", flush=True, file=sys.stderr)

            canvas = Image.new('RGBA', (psd.width, psd.height), (0, 0, 0, 0))
            layer_count = 0
            hidden_view = False

            for layer in psd:
                try:
                    lname = sanitize_name(layer.name).lower()
                    if lname == 'view':
                        hidden_view = True
                        continue  # 跳过view图层
                    if hasattr(layer, 'visible') and not layer.visible:
                        continue
                    li = layer.composite()
                    if li is None:
                        continue
                    if li.mode != 'RGBA':
                        li = li.convert('RGBA')
                    left = getattr(layer, 'left', 0)
                    top = getattr(layer, 'top', 0)
                    canvas.paste(li, (max(0, left), max(0, top)), li)
                    layer_count += 1
                except Exception as le:
                    print(f"  预览合成跳过图层 {getattr(layer, 'name', 'unknown')}: {le}", flush=True, file=sys.stderr)
                    continue

            print(f"预览图层合成完成: 使用图层 {layer_count} 个，view已隐藏={hidden_view}", flush=True, file=sys.stderr)
            final_image = canvas
            # 对预览PNG按透明像素进行边缘裁切（不叠加背景，保留透明度）
            try:
                if final_image.mode != 'RGBA':
                    final_image = final_image.convert('RGBA')
                alpha = final_image.split()[-1]
                bbox = alpha.getbbox()
                if bbox:
                    trimmed = final_image.crop(bbox)
                    final_image = trimmed
                    print(f"预览图透明边裁切: bbox={bbox}, 新尺寸: {final_image.width}×{final_image.height}", flush=True, file=sys.stderr)
                else:
                    print("预览图完全透明或无法计算bbox，跳过裁切", flush=True, file=sys.stderr)
            except Exception as te:
                print(f"预览图裁切透明边失败: {te}", flush=True, file=sys.stderr)

            print(f"合成图像成功，保存到: {preview_path}", flush=True, file=sys.stderr)
            final_image.save(preview_path, 'PNG')
            
            print(f"最终预览图生成成功: {preview_filename}", flush=True, file=sys.stderr)
            return True, str(preview_path)
            
        except Exception as e:
            print(f"生成最终预览图失败: {e}", flush=True, file=sys.stderr)
            print(f"预览图生成错误详情: {traceback.format_exc()}", flush=True, file=sys.stderr)
            return False, str(e)
    
    def delete_template(self, template_id):
        """删除模板"""
        try:
            templates = self._load_templates_index()
            template_to_delete = None
            
            # 找到要删除的模板
            for i, template in enumerate(templates):
                if template['id'] == template_id:
                    template_to_delete = template
                    templates.pop(i)
                    break
            
            if not template_to_delete:
                return False, "模板不存在"
            
            # 删除PSD文件
            template_file = self.templates_dir / template_to_delete['savedFileName']
            if template_file.exists():
                template_file.unlink()
            
            # 删除预览图
            if template_to_delete.get('previewImage'):
                preview_file = self.previews_dir / template_to_delete['previewImage']
                if preview_file.exists():
                    preview_file.unlink()
            
            # 删除参考图
            if template_to_delete.get('referenceImage'):
                reference_file = self.references_dir / template_to_delete['referenceImage']
                if reference_file.exists():
                    reference_file.unlink()
            
            # 删除展开PSD（restoredFileName）
            if template_to_delete.get('restoredFileName'):
                restored_file = self.inside_dir / template_to_delete['restoredFileName']
                if restored_file.exists():
                    restored_file.unlink()

            # 删除 stroke 版本 PSD
            stroke_versions = template_to_delete.get('strokeVersions') or {}
            for k, fname in list(stroke_versions.items()):
                try:
                    fpath = self.inside_stroke_v2_dir / fname
                    if fpath.exists():
                        fpath.unlink()
                except Exception as e:
                    print(f"删除stroke版本失败 {k}: {e}", file=sys.stderr)

            # 删除 stroke 参考图 PNG
            stroke_refs = template_to_delete.get('strokeReferences') or {}
            for k, fname in list(stroke_refs.items()):
                try:
                    fpath = self.references_dir / fname
                    if fpath.exists():
                        fpath.unlink()
                except Exception as e:
                    print(f"删除stroke参考图失败 {k}: {e}", file=sys.stderr)
            
            # 更新索引
            self._save_templates_index(templates)
            
            return True, "模板删除成功"
            
        except Exception as e:
            return False, f"删除模板失败: {str(e)}"
    
    def get_template_file_path(self, template_id):
        """获取模板文件路径"""
        template = self.get_template_by_id(template_id)
        if template:
            return self.templates_dir / template['savedFileName']
        return None
    
    def get_preview_file_path(self, template_id):
        """获取预览图文件路径"""
        template = self.get_template_by_id(template_id)
        if template and template.get('previewImage'):
            return self.previews_dir / template['previewImage']
        return None
    
    def get_reference_file_path(self, template_id):
        """获取参考图文件路径"""
        template = self.get_template_by_id(template_id)
        if template and template.get('referenceImage'):
            return self.references_dir / template['referenceImage']
        return None
    
    def get_inside_file_path(self, template_id):
        """获取展开PSD文件路径"""
        template = self.get_template_by_id(template_id)
        if template and template.get('insideFileName'):
            return self.inside_dir / template['insideFileName']
        return None

    # ===== 部件管理相关方法 =====
    
    def validate_component(self, file, template):
        """验证部件文件"""
        try:
            # 检查文件格式
            if not file.filename.lower().endswith('.png'):
                return False, "只支持PNG格式文件"
            
            # 检查文件内容
                image = Image.open(file)
            
            # 检查尺寸是否与view图层一致
            view_layer = template.get('viewLayer')
            if not view_layer:
                return False, "模板缺少view图层信息"
            
            required_width = view_layer['width']
            required_height = view_layer['height']
            
            if image.size != (required_width, required_height):
                return False, f"尺寸不匹配，要求: {required_width}×{required_height}px，实际: {image.width}×{image.height}px"
            
            # 检查文件不为空
            file.seek(0, 2)  # 移到文件末尾
            file_size = file.tell()
            file.seek(0)  # 重置指针
            
            if file_size == 0:
                return False, "文件为空"
            
            return True, ""
            
        except Exception as e:
            return False, f"验证失败: {str(e)}"

    def generate_unique_component_name(self, base_name, existing_components):
        """生成唯一的部件名称，避免冲突"""
        existing_names = {comp['name'] for comp in existing_components}
        
        if base_name not in existing_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        return f"{base_name}_{counter}"

    def save_component(self, template_id, file, component_name):
        """保存部件到模板"""
        try:
            # 获取模板信息
            template = self.get_template_by_id(template_id)
            if not template:
                return False, "模板不存在"
            
            # 验证部件
            is_valid, error_msg = self.validate_component(file, template)
            if not is_valid:
                return False, error_msg
            
            # 生成部件ID和文件名
            component_id = f"comp_{int(time.time() * 1000)}"
            component_filename = f"{template_id}_{component_id}.png"
            component_path = self.components_dir / component_filename
            
            # 保存文件
            file.seek(0)
            with open(component_path, 'wb') as f:
                f.write(file.read())
            
            # 获取文件信息
                file.seek(0)
            image = Image.open(file)
            file_size = component_path.stat().st_size
            
            # 创建部件记录
            component_record = {
                'id': component_id,
                'name': component_name,
                'fileName': component_filename,
                'originalName': file.filename,
                'uploadedAt': datetime.now().isoformat(),
                'size': file_size,
                'dimensions': {
                    'width': image.width,
                    'height': image.height
                }
            }
            
            # 更新模板记录
            templates = self._load_templates_index()
            for i, tmpl in enumerate(templates):
                if tmpl['id'] == template_id:
                    if 'components' not in tmpl:
                        tmpl['components'] = []
                    tmpl['components'].append(component_record)
                    templates[i] = tmpl
                    break
            
            self._save_templates_index(templates)
            
            print(f"部件保存成功: {component_filename}")
            return True, component_record
            
        except Exception as e:
            print(f"保存部件失败: {e}")
            return False, str(e)

    def get_template_components(self, template_id):
        """获取模板的所有部件"""
        template = self.get_template_by_id(template_id)
        if template:
            return template.get('components', [])
        return []

    def get_component_file_path(self, template_id, component_id):
        """获取部件文件路径"""
        components = self.get_template_components(template_id)
        for comp in components:
            if comp['id'] == component_id:
                return self.components_dir / comp['fileName']
        return None

    def delete_component(self, template_id, component_id):
        """删除部件"""
        try:
            # 获取部件文件路径
            component_path = self.get_component_file_path(template_id, component_id)
            if not component_path or not component_path.exists():
                return False, "部件文件不存在"
            
            # 删除文件
            component_path.unlink()
            
            # 更新模板记录
            templates = self._load_templates_index()
            for i, tmpl in enumerate(templates):
                if tmpl['id'] == template_id:
                    if 'components' in tmpl:
                        tmpl['components'] = [c for c in tmpl['components'] if c['id'] != component_id]
                        templates[i] = tmpl
                    break
            
            self._save_templates_index(templates)
            return True, "删除成功"
            
        except Exception as e:
            return False, str(e)

    def update_component_name(self, template_id, component_id, new_name):
        """更新部件名称"""
        try:
            templates = self._load_templates_index()
            for i, tmpl in enumerate(templates):
                if tmpl['id'] == template_id:
                    if 'components' in tmpl:
                        # 检查名称冲突
                        existing_names = {c['name'] for c in tmpl['components'] if c['id'] != component_id}
                        if new_name in existing_names:
                            return False, "名称已存在"
                        
                        # 更新名称
                        for j, comp in enumerate(tmpl['components']):
                            if comp['id'] == component_id:
                                tmpl['components'][j]['name'] = new_name
                                templates[i] = tmpl
                                self._save_templates_index(templates)
                                return True, "更新成功"
                    break
            
            return False, "部件不存在"
            
        except Exception as e:
            return False, str(e)

    def _add_window_layer(self, final_psd_path, template_id, component_id, result_id):
        """在final.psd最上层添加window图层"""
        try:
            # 统一路径类型
            if isinstance(final_psd_path, str):
                final_psd_path = Path(final_psd_path)

            # 获取部件文件路径（上层已验证存在性）
            component_path = self.get_component_file_path(template_id, component_id)
            
            # 获取模板信息以获取view图层位置
            template = self.get_template_by_id(template_id)
            if not template or not template.get('viewLayer'):
                return False, "模板缺少view图层信息"
            
            view_layer = template['viewLayer']
            view_left = view_layer['left']
            view_top = view_layer['top']
            
            print(f"添加window图层: 部件={component_path.name}, 位置=({view_left}, {view_top})")

            # 打开final.psd，准备重建带新增图层的PSD
        
            psd = PSDImage.open(str(final_psd_path))

            canvas_w, canvas_h = psd.width, psd.height

            # 定位final.psd中的view图层位置和尺寸，确保window与其完全重叠
            final_view_left, final_view_top = None, None
            final_view_width, final_view_height = None, None
            view_layer = None
            try:
                for lyr in psd:
                    if sanitize_name(getattr(lyr, 'name', '')).lower() == 'view':
                        final_view_left = getattr(lyr, 'left', 0)
                        final_view_top = getattr(lyr, 'top', 0)
                        final_view_width = getattr(lyr, 'width', 0)
                        final_view_height = getattr(lyr, 'height', 0)
                        view_layer = lyr
                        break
            except Exception as e:
                raise Exception(f"读取PSD图层信息失败: {e}")
            
            if final_view_left is None or final_view_top is None or view_layer is None:
                raise Exception("最终PSD中未找到view图层")
            if final_view_width <= 0 or final_view_height <= 0:
                raise Exception(f"view图层尺寸无效: {final_view_width}x{final_view_height}")

            # 收集原PSD的所有图层为扁平化像素图，但保留每层的独立性
            layers_data = []
            for layer in psd:
                try:
                    layer_img = layer.composite()
                    if layer_img is None:
                        continue
                    if layer_img.mode != 'RGBA':
                        layer_img = layer_img.convert('RGBA')
                    left = getattr(layer, 'left', 0)
                    top = getattr(layer, 'top', 0)
                    # 记录图层
                    layers_data.append({
                        'name': sanitize_name(layer.name),
                        'image': layer_img,
                        'position': (max(0, left), max(0, top)),
                        'visible': bool(getattr(layer, 'visible', True))
                    })
                except Exception as layer_error:
                    print(f"  跳过原图层 {getattr(layer, 'name', 'unknown')}: {layer_error}")
                    continue

            # 加载并缩放window组件到view图层尺寸
            print(f"加载部件: {component_path}")
            component_img = Image.open(component_path).convert('RGBA')
            original_size = component_img.size
            target_size = (int(final_view_width), int(final_view_height))
            
            print(f"部件原始尺寸: {original_size}, 目标尺寸: {target_size}")
            
            # 如果尺寸不匹配，强制缩放到目标尺寸
            if original_size != target_size:
                try:
                    # 强制拉伸到目标尺寸（不保持宽高比）
                    scaled_component_img = component_img.resize(target_size, Image.LANCZOS)
                    print(f"部件已缩放从 {original_size} 到 {target_size}")
                except Exception as e:
                    raise Exception(f"部件缩放失败: {e}")
            else:
                scaled_component_img = component_img
                print("部件尺寸匹配，无需缩放")
            
            # 生成临时缩放后的部件文件（用于调试和备份）
            temp_component_path = final_psd_path.parent / f"temp_scaled_component_{result_id}.png"
            try:
                scaled_component_img.save(temp_component_path)
                print(f"临时缩放部件已保存: {temp_component_path}")
            except Exception as e:
                raise Exception(f"保存临时缩放部件失败: {e}")
            
            # 追加缩放后的window组件为新的最上层图层
            layers_data.append({
                'name': 'window',
                'image': scaled_component_img,
                'position': (int(final_view_left), int(final_view_top)),
                'visible': True
            })

            # 备份原final.psd
            backup_path = final_psd_path.with_suffix('.backup.psd')
            shutil.copy2(final_psd_path, backup_path)

            # 使用内部PSD写入器创建带图层的真实PSD
            psd_bytes = self._create_layered_psd_data(layers_data, canvas_w, canvas_h)
            with open(final_psd_path, 'wb') as f:
                f.write(psd_bytes)

            print(f"Window图层添加完成（真实PSD层），原文件已备份到: {backup_path}")
            
            # 清理临时文件
            try:
                if temp_component_path.exists():
                    temp_component_path.unlink()
                    print(f"已清理临时缩放部件文件: {temp_component_path}")
            except Exception as cleanup_error:
                print(f"清理临时文件失败（非致命错误）: {cleanup_error}")
            
            return True, str(final_psd_path)
            
        except Exception as e:
            print(f"添加window图层失败: {e}")
            print(traceback.format_exc())
            
            # 异常时也要清理可能存在的临时文件
            try:
                temp_component_path = final_psd_path.parent / f"temp_scaled_component_{result_id}.png"
                if temp_component_path.exists():
                    temp_component_path.unlink()
                    print(f"异常清理临时文件: {temp_component_path}")
            except:
                pass
            
            # 严格模式：直接抛出异常而不是返回False
            raise e

    # ===== 索引维护方法 =====

    def _load_results_index(self):
        """加载索引文件"""
        try:
            if self.results_index_file.exists():
                with open(self.results_index_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)

                # 兼容历史格式：若为列表或results为列表，则规范化为字典映射
                def _normalize(items_list):
                    results_map = {}
                    if isinstance(items_list, list):
                        for item in items_list:
                            if not isinstance(item, dict):
                                continue
                            rid = (
                                item.get('id') or
                                item.get('resultId') or
                                item.get('result_id')
                            )
                            if not rid:
                                continue
                            results_map[rid] = {
                                "id": rid,
                                "template_id": item.get('template_id') or item.get('templateId'),
                                "template_name": item.get('template_name') or item.get('templateName') or '',
                                "created_at": item.get('created_at') or item.get('createdAt') or datetime.now().isoformat(),
                                "final_psd_size": item.get('final_psd_size') or item.get('finalPsdSize') or 0,
                            }
                    return {
                        "version": "1.0",
                        "last_updated": datetime.now().isoformat(),
                        "results": results_map
                    }

                # 情况1：整个文件就是一个列表（旧格式）
                if isinstance(raw, list):
                    return _normalize(raw)

                # 情况2：是字典，但results键不存在或为列表
                if isinstance(raw, dict):
                    if isinstance(raw.get('results'), list):
                        return _normalize(raw.get('results') or [])
                    # 确保必要字段存在
                    if 'results' not in raw or not isinstance(raw.get('results'), dict):
                        raw['results'] = {}
                    if 'version' not in raw:
                        raw['version'] = '1.0'
                    if 'last_updated' not in raw:
                        raw['last_updated'] = datetime.now().isoformat()
                    return raw

                # 兜底：返回空结构
                return {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "results": {}
                }
            else:
                return {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "results": {}
                }
        except Exception as e:
            print(f"加载索引文件失败: {e}", file=sys.stderr)
            return {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "results": {}
            }

    def _save_results_index(self, index_data):
        """保存索引文件"""
        try:
            index_data["last_updated"] = datetime.now().isoformat()
            with open(self.results_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存索引文件失败: {e}", file=sys.stderr)
            return False

    def _add_to_results_index(self, result_id, template_id, template_name, used_stroke_width=None):
        """新增结果到索引"""
        try:
            index_data = self._load_results_index()

            # 获取PSD文件大小
            psd_path = self.result_downloads_dir / f"{result_id}_final.psd"
            final_psd_size = psd_path.stat().st_size if psd_path.exists() else 0

            entry = {
                "id": result_id,
                "template_id": template_id,
                "template_name": template_name,
                "created_at": datetime.now().isoformat(),
                "final_psd_size": final_psd_size
            }
            if used_stroke_width is not None:
                entry["used_stroke_width"] = int(used_stroke_width)

            index_data["results"][result_id] = entry

            return self._save_results_index(index_data)
        except Exception as e:
            print(f"添加索引记录失败: {e}", file=sys.stderr)
            return False

    def _remove_from_results_index(self, result_id):
        """从索引中删除结果"""
        try:
            index_data = self._load_results_index()
            if result_id in index_data["results"]:
                del index_data["results"][result_id]
                return self._save_results_index(index_data)
            return True
        except Exception as e:
            print(f"删除索引记录失败: {e}", file=sys.stderr)
            return False

    def _update_results_index(self, result_id, **updates):
        """更新索引中的结果信息"""
        try:
            index_data = self._load_results_index()
            if result_id in index_data["results"]:
                index_data["results"][result_id].update(updates)
                return self._save_results_index(index_data)
            return False
        except Exception as e:
            print(f"更新索引记录失败: {e}", file=sys.stderr)
            return False


# 创建全局实例
processor_core = PSDProcessorCore()
