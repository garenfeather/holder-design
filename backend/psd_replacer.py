#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PSD模板图片替换器
功能：根据PSD模板中part1-4图层的选区，从源图片中截取对应部位并替换图层内容

流程：
1. 读取PSD模板，验证包含part1-4图层
2. 读取与模板同尺寸的源图片
3. 根据part1-4图层边界截取源图片对应部位
4. 二进制复制PSD模板
5. 将截取的图片部位替换对应的part图层
6. 输出替换后的PSD文件
"""

from psd_tools import PSDImage
from PIL import Image, ImageOps
import struct
import io
from pathlib import Path

from utils.strings import sanitize_name

class PSDReplacer:
    def replace(self, template_path, source_image_path, output_path):
        self.template_path = Path(template_path)
        self.source_image_path = Path(source_image_path)
        self.output_path = Path(output_path)
        self.part_layers = ["part1", "part2", "part3", "part4"]

        try:
            print("=" * 60)
            print("[TARGET] PSD模板图片替换器")
            print("=" * 60)
            
            # 1. 加载验证
            if not self.load_and_validate():
                print("[ERROR] 加载验证失败")
                return False
            
            # 2. 截取图片部位
            if not self.extract_parts():
                print("[ERROR] 截取图片部位失败")
                return False
            
            # 3. 创建替换PSD
            if not self.create_replaced_psd():
                print("[ERROR] 创建替换PSD失败")
                return False
            
            # 4. 最终验证
            if not self.output_path.exists():
                print("[ERROR] 输出文件未生成")
                return False
            
            file_size = self.output_path.stat().st_size
            if file_size == 0:
                print("[ERROR] 输出文件为空")
                return False
            
            print("\n" + "=" * 60)
            print("[SUCCESS] 替换完成!")
            print(f"[FILE] 模板: {self.template_path.name}")
            print(f"[FILE] 源图片: {self.source_image_path.name}")
            print(f"[FILE] 输出: {self.output_path.name} ({file_size} bytes)")
            print(f"📐 尺寸: {self.template.width}×{self.template.height}")
            print(f"[PROCESS] 已替换: {', '.join(self.cropped_parts.keys())}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 替换失败: {e}")
            import traceback
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            return False

    def load_and_validate(self):
        """加载并验证模板PSD和源图片"""
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

            # 对用户上传的图片进行左右翻转
            self.source_image = ImageOps.mirror(self.source_image)
            print(f"  ✓ 已对源图片进行左右翻转")
        except Exception as e:
            print(f"[ERROR] 加载源图片失败: {e}")
            return False

        # 验证尺寸匹配
        if (self.template.width, self.template.height) != self.source_image.size:
            print(f"[ERROR] 尺寸不匹配: 模板{self.template.width}×{self.template.height} vs 图片{self.source_image.size[0]}×{self.source_image.size[1]}")
            return False
        
        print("  ✓ 尺寸匹配")
        
        return self._detect_part_layers()
    
    def _detect_part_layers(self):
        """检测part1-4图层"""
        print("[SEARCH] 检测part图层...")
        
        self.layers = {}
        found_parts = []
        
        for layer in self.template:
            # 清理图层名称
            clean_name = sanitize_name(layer.name).lower()
            print(f"  检查图层: '{layer.name}' -> '{clean_name}'")
            if clean_name in self.part_layers:
                bounds = self._get_layer_bounds(layer)
                if bounds:
                    self.layers[clean_name] = {
                        'layer': layer,
                        'bounds': bounds
                    }
                    found_parts.append(clean_name)
                    print(f"  找到 {layer.name}: 位置({bounds['x1']},{bounds['y1']}) 尺寸({bounds['width']}×{bounds['height']})")
        
        missing = [p for p in self.part_layers if p not in found_parts]
        if missing:
            print(f"[ERROR] 缺少part图层: {', '.join(missing)}")
            return False
        
        print("  ✓ 所有part图层检测完成")
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
    
    def extract_parts(self):
        """根据part图层的实际形状截取源图片"""
        print(f"\n[CUT]  截取图片部位")
        
        self.cropped_parts = {}
        
        for part_name, info in self.layers.items():
            layer = info['layer']
            bounds = info['bounds']
            
            # 获取图层的实际图像数据（包括透明度）
            layer_image = layer.composite()
            if not layer_image:
                print(f"  [WARNING]  跳过 {part_name}: 无法获取图层图像")
                continue
            
            # 确保图层图像为RGBA格式
            if layer_image.mode != 'RGBA':
                layer_image = layer_image.convert('RGBA')
            
            # 确保边界在图片范围内
            x1 = max(0, bounds['x1'])
            y1 = max(0, bounds['y1'])
            x2 = min(self.source_image.size[0], bounds['x2'])
            y2 = min(self.source_image.size[1], bounds['y2'])
            
            if x2 > x1 and y2 > y1:
                # 从源图片中截取对应区域
                source_crop = self.source_image.crop((x1, y1, x2, y2))
                
                # 获取图层在该区域的蒙版（透明度信息）
                layer_crop = layer_image.crop((0, 0, x2-x1, y2-y1))
                
                # 创建一个新图像，使用图层的形状作为蒙版
                result_image = Image.new('RGBA', (x2-x1, y2-y1), (0, 0, 0, 0))
                
                # 使用图层的alpha通道作为蒙版，将源图片内容按图层形状剪切
                source_pixels = list(source_crop.getdata())
                layer_pixels = list(layer_crop.getdata())
                result_pixels = []
                
                for i in range(len(source_pixels)):
                    src_r, src_g, src_b, src_a = source_pixels[i]
                    layer_r, layer_g, layer_b, layer_a = layer_pixels[i]
                    
                    # 使用图层的alpha作为蒙版，保留源图片的颜色
                    if layer_a > 0:  # 图层在此处不透明
                        result_pixels.append((src_r, src_g, src_b, layer_a))
                    else:  # 图层在此处透明
                        result_pixels.append((0, 0, 0, 0))
                
                result_image.putdata(result_pixels)
                
                self.cropped_parts[part_name] = {
                    'image': result_image,
                    'position': (x1, y1),
                    'bounds': bounds
                }
                print(f"  截取 {part_name}: 按图层形状截取 {result_image.size[0]}×{result_image.size[1]}")
        
        print(f"  ✓ 截取完成，共 {len(self.cropped_parts)} 个部位")
        return True
    
    def create_replaced_psd(self):
        """创建替换后的PSD文件"""
        print(f"\n📋 创建替换后的PSD")
        
        try:
            print(f"  截取的部位数量: {len(self.cropped_parts)}")
            for part_name in self.cropped_parts.keys():
                print(f"  - {part_name}")
            
            # 生成新的PSD文件内容（不再复制模板）
            self._write_replaced_psd()
            
            print(f"  ✓ part图层替换完成")
            return True
            
        except Exception as e:
            print(f"[ERROR] 创建替换PSD失败: {e}")
            import traceback
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            return False
    
    def _write_replaced_psd(self):
        """写入替换后的PSD文件内容"""
        print(f"  收集图层数据...")
        # 收集所有图层数据
        all_layers = []
        
        # 重新打开模板获取所有图层
        template = PSDImage.open(str(self.template_path))
        print(f"  模板总图层数: {len(list(template))}")
        
        for layer in template:
            # 清理图层名称
            clean_name = sanitize_name(layer.name).lower()
            print(f"  处理图层: {layer.name} ({clean_name})")
            
            if clean_name in self.cropped_parts:
                # 使用截取的图片替换part图层
                part_data = self.cropped_parts[clean_name]
                all_layers.append({
                    'name': sanitize_name(layer.name),
                    'image': part_data['image'],
                    'position': part_data['position']
                })
                print(f"    ✓ 替换: {layer.name}")
            else:
                # 保留其他图层
                layer_image = layer.composite()
                if layer_image:
                    bounds = self._get_layer_bounds(layer)
                    if bounds and layer_image.mode != 'RGBA':
                        layer_image = layer_image.convert('RGBA')
                    if bounds:
                        all_layers.append({
                            'name': sanitize_name(layer.name),
                            'image': layer_image,
                            'position': (bounds['x1'], bounds['y1'])
                        })
                        print(f"    ✓ 保留: {layer.name}")
                    else:
                        print(f"    [WARNING] 跳过无边界图层: {layer.name}")
                else:
                    print(f"    [WARNING] 跳过无图像图层: {layer.name}")
        
        print(f"  最终图层数量: {len(all_layers)}")
        # 写入PSD文件
        self._save_psd(all_layers)
    
    def _save_psd(self, layers):
        """保存PSD文件"""
        try:
            print(f"  开始保存PSD文件到: {self.output_path}")
            print(f"  图层数量: {len(layers)}")
            
            canvas_width = self.template.width
            canvas_height = self.template.height
            print(f"  画布尺寸: {canvas_width} x {canvas_height}")
            
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
                
                # 图层和蒙版信息段
                layer_info = io.BytesIO()
                print(f"  写入图层信息...")
                self._write_layers(layer_info, layers, canvas_width, canvas_height)
                layer_data = layer_info.getvalue()
                print(f"  图层数据长度: {len(layer_data)} bytes")
                f.write(struct.pack('>I', len(layer_data)))
                f.write(layer_data)
                
                # 合成图像
                print(f"  写入合成图像...")
                f.write(struct.pack('>H', 0))
                self._write_composite(f, layers, canvas_width, canvas_height)
                
                # 强制刷新文件缓冲区
                f.flush()
                
            print(f"  文件写入完成")
            
            # 验证文件已创建
            if self.output_path.exists():
                file_size = self.output_path.stat().st_size
                print(f"  文件存在，大小: {file_size} bytes")
                if file_size > 0:
                    print(f"  ✓ PSD文件已保存: {self.output_path} ({file_size} bytes)")
                else:
                    print(f"  [ERROR] PSD文件为空")
                    raise Exception("PSD文件保存后为空")
            else:
                print(f"  [ERROR] PSD文件不存在")
                raise Exception("PSD文件未生成")
                
        except Exception as e:
            print(f"  [ERROR] 保存PSD文件时发生错误: {e}")
            import traceback
            print(f"  错误详情: {traceback.format_exc()}")
            # 如果保存失败，尝试简单的复制方案
            try:
                print(f"  尝试降级保存方案...")
                self._fallback_save_psd(layers)
            except Exception as fallback_error:
                print(f"  [ERROR] 降级保存方案也失败: {fallback_error}")
                raise e
    
    def _write_layers(self, f, layers, canvas_width, canvas_height):
        """写入图层数据"""
        # 图层信息长度占位符
        start_pos = f.tell()
        f.write(struct.pack('>I', 0))
        
        # 图层计数
        f.write(struct.pack('>h', -len(layers)))
        
        # 图层记录
        for layer in layers:
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
            f.write(struct.pack('>I', y))         # top
            f.write(struct.pack('>I', x))         # left
            f.write(struct.pack('>I', y + h))     # bottom
            f.write(struct.pack('>I', x + w))     # right
            
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
            
            # 蒙版（空）
            f.write(struct.pack('>I', 0))
            # 混合范围（空）
            f.write(struct.pack('>I', 0))
            
            # 图层名称
            name_bytes = layer['name'].encode('ascii')[:255]
            f.write(struct.pack('>B', len(name_bytes)))
            f.write(name_bytes)
            
            # 4字节对齐
            total_len = 1 + len(name_bytes)
            padding = (4 - (total_len % 4)) % 4
            f.write(b'\x00' * padding)
            
            # 更新额外数据长度
            extra_end = f.tell()
            f.seek(extra_start)
            f.write(struct.pack('>I', extra_end - extra_start - 4))
            f.seek(extra_end)
        
        # 图层图像数据
        for layer in layers:
            self._write_layer_data(f, layer, canvas_width, canvas_height)
        
        # 更新图层信息长度
        end_pos = f.tell()
        f.seek(start_pos)
        f.write(struct.pack('>I', end_pos - start_pos - 4))
        f.seek(end_pos)
    
    def _write_layer_data(self, f, layer, canvas_width, canvas_height):
        """写入单个图层数据"""
        image = layer['image']
        x, y = layer['position']
        x = max(0, int(x))
        y = max(0, int(y))
        
        # 边界检查和裁剪
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
    
    def _write_composite(self, f, layers, canvas_width, canvas_height):
        """写入合成图像"""
        # 创建合成画布
        composite = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
        
        # 合成所有图层
        for layer in layers:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            
            if x < canvas_width and y < canvas_height:
                composite.paste(layer['image'], (x, y), layer['image'])
        
        # 写入合成数据
        pixels = list(composite.getdata())
        for channel_idx in [0, 1, 2, 3]:  # R, G, B, A
            for pixel in pixels:
                f.write(struct.pack('>B', pixel[channel_idx]))
    
    def _fallback_save_psd(self, layers):
        """降级保存方案：保存为PNG但扩展名是PSD"""
        print(f"  尝试降级保存方案...")
        
        # 创建合成图像
        canvas_width = self.template.width
        canvas_height = self.template.height
        composite = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
        
        # 合成所有图层
        for layer in layers:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            
            if x < canvas_width and y < canvas_height:
                try:
                    composite.paste(layer['image'], (x, y), layer['image'])
                except Exception as e:
                    print(f"  警告: 图层合成失败: {e}")
        
        # 先尝试保存为PNG，验证图像是否正常
        try:
            composite.save(str(self.output_path), 'PNG')
            print(f"  ✓ 降级保存完成（PNG格式）: {self.output_path}")
            
            # 验证文件
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                print(f"  文件大小: {size} bytes")
            
        except Exception as e:
            print(f"  [ERROR] 降级保存也失败: {e}")
            raise e
