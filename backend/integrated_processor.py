#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
"""集成的PSD处理器 - 集成自scripts/integrated_processor.py"""

from psd_tools import PSDImage
from utils.strings import sanitize_name
from PIL import Image, ImageOps
import shutil
import struct
import io
from pathlib import Path
import tempfile


class IntegratedProcessor:
    """整合式PSD处理器 - 结合图片替换和模板变换的完整流程"""
    
    def __init__(self, template_path, source_image_path, output_path=None):
        self.template_path = Path(template_path)
        self.source_image_path = Path(source_image_path)
        self.output_path = Path(output_path) if output_path else self._generate_output_path()
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]
        
    def _generate_output_path(self):
        """生成输出文件路径"""
        return self.template_path.with_name(f"{self.template_path.stem}_processed.psd")
    
    def load_and_validate(self):
        """加载并验证输入文件"""
        print(f"📂 加载模板PSD和源图片")
        
        # 加载PSD模板
        try:
            self.template = PSDImage.open(str(self.template_path))
            print(f"  模板PSD: {self.template.width}×{self.template.height} px")
        except Exception as e:
            print(f"[ERROR] 加载PSD模板失败: {e}")
            return False
        
        # 加载源图片
        try:
            self.source_image = Image.open(str(self.source_image_path))
            if self.source_image.mode != 'RGBA':
                self.source_image = self.source_image.convert('RGBA')
            print(f"  源图片: {self.source_image.size[0]}×{self.source_image.size[1]} px")
        except Exception as e:
            print(f"[ERROR] 加载源图片失败: {e}")
            return False
        
        # 验证尺寸匹配
        if (self.template.width, self.template.height) != self.source_image.size:
            print(f"[ERROR] 尺寸不匹配: 模板{self.template.width}×{self.template.height} vs 图片{self.source_image.size[0]}×{self.source_image.size[1]}")
            return False
        
        print("  ✓ 尺寸匹配")
        return self._detect_layers()
    
    def _detect_layers(self):
        """检测必要图层"""
        print("[SEARCH] 检测图层...")
        
        self.layers = {}
        found_layers = []
        
        for layer in self.template:
            layer_name = sanitize_name(layer.name).lower()
            if layer_name in self.required_layers:
                bounds = self._get_layer_bounds(layer)
                if bounds:
                    self.layers[layer_name] = {
                        'layer': layer,
                        'bounds': bounds
                    }
                    found_layers.append(layer_name)
                    print(f"  找到 {layer.name}: 位置({bounds['x1']},{bounds['y1']}) 尺寸({bounds['width']}×{bounds['height']})")
        
        missing = [p for p in self.required_layers if p not in found_layers]
        if missing:
            print(f"[ERROR] 缺少图层: {', '.join(missing)}")
            return False
        
        print("  ✓ 所有必要图层检测完成")
        return True
    
    def _get_layer_bounds(self, layer):
        """获取图层边界"""
        try:
            if not layer.bbox:
                return None
            x1, y1, x2, y2 = layer.bbox
            return {
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'width': x2 - x1, 'height': y2 - y1
            }
        except:
            return None
    
    def replace_parts(self):
        """按图层形状替换part图层内容"""
        print(f"\n[CUT]  替换part图层内容")
        
        self.processed_layers = []
        
        for layer in self.template:
            layer_name = sanitize_name(layer.name).lower()
            
            if layer_name.startswith('part') and layer_name in self.layers:
                # 替换part图层
                layer_info = self.layers[layer_name]
                replaced_image = self._extract_part_by_shape(layer_info)
                if replaced_image:
                    self.processed_layers.append({
                        'name': sanitize_name(layer.name),
                        'image': replaced_image,
                        'bounds': layer_info['bounds']
                    })
                    print(f"  替换: {layer.name}")
            else:
                # 保留其他图层
                layer_image = layer.composite()
                if layer_image:
                    bounds = self._get_layer_bounds(layer)
                    if bounds:
                        if layer_image.mode != 'RGBA':
                            layer_image = layer_image.convert('RGBA')
                        self.processed_layers.append({
                            'name': sanitize_name(layer.name),
                            'image': layer_image,
                            'bounds': bounds
                        })
                        print(f"  保留: {layer.name}")
        
        print(f"  ✓ 图层处理完成，共 {len(self.processed_layers)} 个图层")
        return True
    
    def _extract_part_by_shape(self, layer_info):
        """根据图层形状截取源图片"""
        layer = layer_info['layer']
        bounds = layer_info['bounds']
        
        # 获取图层的实际形状
        layer_image = layer.composite()
        if not layer_image:
            return None
            
        if layer_image.mode != 'RGBA':
            layer_image = layer_image.convert('RGBA')
        
        # 确保边界在图片范围内
        x1 = max(0, bounds['x1'])
        y1 = max(0, bounds['y1'])
        x2 = min(self.source_image.size[0], bounds['x2'])
        y2 = min(self.source_image.size[1], bounds['y2'])
        
        if x2 <= x1 or y2 <= y1:
            return None
        
        # 从源图片截取对应区域
        source_crop = self.source_image.crop((x1, y1, x2, y2))
        layer_crop = layer_image.crop((0, 0, x2-x1, y2-y1))
        
        # 按图层形状剪切
        source_pixels = list(source_crop.getdata())
        layer_pixels = list(layer_crop.getdata())
        result_pixels = []
        
        for i in range(len(source_pixels)):
            src_r, src_g, src_b, src_a = source_pixels[i]
            layer_r, layer_g, layer_b, layer_a = layer_pixels[i]
            
            if layer_a > 0:
                result_pixels.append((src_r, src_g, src_b, layer_a))
            else:
                result_pixels.append((0, 0, 0, 0))
        
        result_image = Image.new('RGBA', (x2-x1, y2-y1), (0, 0, 0, 0))
        result_image.putdata(result_pixels)
        return result_image
    
    def transform_layers(self):
        """对图层进行变换（画布扩展、移动、翻转）"""
        print(f"\n[TARGET] 进行图层变换")
        
        # 计算新画布尺寸（3.5倍扩展）
        original_width = self.template.width
        original_height = self.template.height
        new_width = int(original_width * 3.5)
        new_height = int(original_height * 3.5)
        center_offset_x = (new_width - original_width) // 2
        center_offset_y = (new_height - original_height) // 2
        
        print(f"  画布扩展: {original_width}×{original_height} → {new_width}×{new_height}")
        
        # 计算part图层尺寸（用于移动计算）
        part_bounds = {}
        for layer_data in self.processed_layers:
            layer_name = layer_data['name'].lower()
            if layer_name.startswith('part'):
                bounds = layer_data['bounds']
                part_bounds[layer_name] = bounds
        
        # 变换每个图层
        self.final_layers = []
        for layer_data in self.processed_layers:
            layer_name = layer_data['name'].lower()
            bounds = layer_data['bounds']
            image = layer_data['image']
            
            # 计算新位置
            centered_x = bounds['x1'] + center_offset_x
            centered_y = bounds['y1'] + center_offset_y
            
            # 应用特定移动
            if layer_name == 'part1':
                final_x = centered_x - part_bounds['part1']['width']
                final_y = centered_y
                image = ImageOps.mirror(image)  # 水平翻转
                print(f"  {layer_data['name']}: 移动并水平翻转")
            elif layer_name == 'part2':
                final_x = centered_x
                final_y = centered_y - part_bounds['part2']['height']
                image = ImageOps.flip(image)  # 垂直翻转
                print(f"  {layer_data['name']}: 移动并垂直翻转")
            elif layer_name == 'part3':
                final_x = centered_x + part_bounds['part3']['width']
                final_y = centered_y
                image = ImageOps.mirror(image)  # 水平翻转
                print(f"  {layer_data['name']}: 移动并水平翻转")
            elif layer_name == 'part4':
                final_x = centered_x
                final_y = centered_y + part_bounds['part4']['height']
                image = ImageOps.flip(image)  # 垂直翻转
                print(f"  {layer_data['name']}: 移动并垂直翻转")
            else:
                final_x = centered_x
                final_y = centered_y
                print(f"  {layer_data['name']}: 中心对齐")
            
            self.final_layers.append({
                'name': layer_data['name'],
                'image': image,
                'position': (final_x, final_y)
            })
        
        self.canvas_size = (new_width, new_height)
        print(f"  ✓ 图层变换完成")
        return True
    
    def save_final_psd(self):
        """保存最终的PSD文件"""
        print(f"\n[SAVE] 保存最终PSD文件")
        
        try:
            canvas_width, canvas_height = self.canvas_size
            
            with open(self.output_path, 'wb') as f:
                # PSD文件头
                f.write(b'8BPS')
                f.write(struct.pack('>H', 1))
                f.write(b'\x00' * 6)
                f.write(struct.pack('>H', 4))
                f.write(struct.pack('>I', canvas_height))
                f.write(struct.pack('>I', canvas_width))
                f.write(struct.pack('>H', 8))
                f.write(struct.pack('>H', 3))
                
                # 颜色模式数据段（空）
                f.write(struct.pack('>I', 0))
                
                # 图像资源段（空）
                f.write(struct.pack('>I', 0))
                
                # 图层信息
                layer_info = io.BytesIO()
                self._write_layer_info(layer_info, canvas_width, canvas_height)
                layer_data = layer_info.getvalue()
                f.write(struct.pack('>I', len(layer_data)))
                f.write(layer_data)
                
                # 合成图像
                f.write(struct.pack('>H', 0))
                self._write_composite_image(f, canvas_width, canvas_height)
            
            print(f"  ✓ 文件保存到: {self.output_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 保存文件失败: {e}")
            return False
    
    def _write_layer_info(self, f, canvas_width, canvas_height):
        """写入图层信息"""
        start_pos = f.tell()
        f.write(struct.pack('>I', 0))  # 占位符
        
        f.write(struct.pack('>h', -len(self.final_layers)))  # 图层数量
        
        # 图层记录
        for layer in self.final_layers:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            w, h = layer['image'].size
            
            # 边界检查
            if x + w > canvas_width:
                w = max(1, canvas_width - x)
            if y + h > canvas_height:
                h = max(1, canvas_height - y)
            
            # 图层边界
            f.write(struct.pack('>I', y))
            f.write(struct.pack('>I', x))
            f.write(struct.pack('>I', y + h))
            f.write(struct.pack('>I', x + w))
            
            # 通道信息
            f.write(struct.pack('>H', 4))
            channel_size = w * h + 2
            for channel_id in [-1, 0, 1, 2]:
                f.write(struct.pack('>h', channel_id))
                f.write(struct.pack('>I', channel_size))
            
            # 混合模式
            f.write(b'8BIM')
            f.write(b'norm')
            f.write(struct.pack('>B', 255))  # 不透明度
            f.write(struct.pack('>B', 0))    # 剪切
            f.write(struct.pack('>B', 0))    # 标志
            f.write(struct.pack('>B', 0))    # 填充
            
            # 额外数据
            extra_start = f.tell()
            f.write(struct.pack('>I', 0))
            
            # 蒙版和混合范围（空）
            f.write(struct.pack('>I', 0))
            f.write(struct.pack('>I', 0))
            
            # 图层名称
            name_bytes = layer['name'].encode('ascii')[:255]
            f.write(struct.pack('>B', len(name_bytes)))
            f.write(name_bytes)
            
            # 填充对齐
            total_len = 1 + len(name_bytes)
            padding = (4 - (total_len % 4)) % 4
            f.write(b'\x00' * padding)
            
            # 更新额外数据长度
            extra_end = f.tell()
            f.seek(extra_start)
            f.write(struct.pack('>I', extra_end - extra_start - 4))
            f.seek(extra_end)
        
        # 图层图像数据
        for layer in self.final_layers:
            self._write_layer_data(f, layer, canvas_width, canvas_height)
        
        # 更新图层信息长度
        end_pos = f.tell()
        f.seek(start_pos)
        f.write(struct.pack('>I', end_pos - start_pos - 4))
        f.seek(end_pos)
    
    def _write_layer_data(self, f, layer, canvas_width, canvas_height):
        """写入图层数据"""
        image = layer['image']
        x, y = layer['position']
        x = max(0, int(x))
        y = max(0, int(y))
        
        if x >= canvas_width or y >= canvas_height:
            for _ in range(4):
                f.write(struct.pack('>H', 0))
            return
        
        crop_w = min(image.width, canvas_width - x)
        crop_h = min(image.height, canvas_height - y)
        
        if crop_w != image.width or crop_h != image.height:
            image = image.crop((0, 0, crop_w, crop_h))
        
        pixels = list(image.getdata())
        
        # 写入4个通道：A, R, G, B
        for channel_idx in [3, 0, 1, 2]:
            f.write(struct.pack('>H', 0))  # 无压缩
            for pixel in pixels:
                f.write(struct.pack('>B', pixel[channel_idx]))
    
    def _write_composite_image(self, f, canvas_width, canvas_height):
        """写入合成图像"""
        composite = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
        
        for layer in self.final_layers:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            
            if x < canvas_width and y < canvas_height:
                composite.paste(layer['image'], (x, y), layer['image'])
        
        pixels = list(composite.getdata())
        for channel_idx in [0, 1, 2, 3]:  # R, G, B, A
            for pixel in pixels:
                f.write(struct.pack('>B', pixel[channel_idx]))
    
    def process(self):
        """执行完整处理流程"""
        try:
            print("=" * 60)
            print("[TARGET] 整合式PSD处理器")
            print("=" * 60)
            
            # 1. 加载验证
            if not self.load_and_validate():
                return False
            
            # 2. 替换part图层
            if not self.replace_parts():
                return False
            
            # 3. 变换图层
            if not self.transform_layers():
                return False
            
            # 4. 保存结果
            if not self.save_final_psd():
                return False
            
            print("\n" + "=" * 60)
            print("[SUCCESS] 处理完成!")
            print(f"[FILE] 模板: {self.template_path.name}")
            print(f"[FILE] 源图片: {self.source_image_path.name}")
            print(f"[FILE] 输出: {self.output_path.name}")
            print(f"📐 画布尺寸: {self.template.width}×{self.template.height} → {self.canvas_size[0]}×{self.canvas_size[1]}")
            print(f"[PROCESS] 处理图层: {len(self.final_layers)} 个")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 处理失败: {e}")
            return False
