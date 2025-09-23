#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PSD裁剪工具 - 集成自scripts/psd_crop_view_parts.py
功能：以view图层为选区裁剪PSD，生成与view同尺寸的PSD文件
"""

# 标准库导入
from typing import Dict

# 第三方库导入
from PIL import Image, ImageChops
from psd_tools import PSDImage

try:
    from pytoshop.user import nested_layers as nl
    import numpy as np
    PYTOSHOP_AVAILABLE = True
except Exception:
    PYTOSHOP_AVAILABLE = False


class PSDCropper:
    """PSD裁剪工具类"""
    
    def __init__(self):
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]
    
    def crop_by_view(self, input_path, output_path):
        """以view图层为选区裁剪PSD文件"""
        try:
            print("🔪 PSD裁剪工具")
            print(f"📂 输入: {input_path}")
            print(f"[FILE] 输出: {output_path}")
            
            # 1. 加载和验证PSD
            psd = PSDImage.open(str(input_path))
            layers = self._load_required_layers(psd)
            if not layers:
                print(f"[ERROR] PSD缺少必要图层: {', '.join(self.required_layers)}")
                return False
            
            # 2. 获取view图层信息
            view_layer = layers['view']
            view_img, view_bbox = self._layer_to_image_and_bbox(view_layer)
            v_left, v_top, v_right, v_bottom = view_bbox
            v_w, v_h = v_right - v_left, v_bottom - v_top
            view_alpha = view_img.split()[3]
            
            print(f"📐 view图层尺寸: {v_w}×{v_h} 像素")
            print(f"📍 view图层位置: ({v_left}, {v_top}) -> ({v_right}, {v_bottom})")
            
            # 3. 处理所有图层
            cropped_images = {'view': view_img}
            
            # 处理part1-4图层
            for name in ['part1', 'part2', 'part3', 'part4']:
                part_layer = layers[name]
                part_img, part_bbox = self._layer_to_image_and_bbox(part_layer)
                cropped = self._crop_part_with_view_mask(part_img, part_bbox, view_bbox, view_alpha)
                cropped_images[name] = cropped
                print(f"  处理图层: {name}")
            
            # 4. 生成裁剪后的PSD
            success = self._build_layered_psd(output_path, (v_w, v_h), cropped_images)
            if success:
                print(f"[SUCCESS] 裁剪完成: {output_path}")
                return True
            else:
                print("[ERROR] 生成PSD失败: pytoshop不可用")
                return False
                
        except Exception as e:
            print(f"[ERROR] 裁剪失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _find_layer_by_name(self, psd: PSDImage, name: str):
        """查找指定名称的图层"""
        for layer in psd.descendants():
            try:
                if getattr(layer, 'name', None) == name and not layer.is_group():
                    return layer
            except Exception:
                if getattr(layer, 'name', None) == name:
                    return layer
        return None
    
    def _load_required_layers(self, psd: PSDImage) -> Dict[str, object]:
        """加载所有必要图层"""
        layers = {}
        for name in self.required_layers:
            layer = self._find_layer_by_name(psd, name)
            if not layer:
                return {}
            layers[name] = layer
        return layers
    
    def _layer_to_image_and_bbox(self, layer) -> (Image.Image, tuple):
        """返回该图层渲染后的RGBA图与bbox"""
        img = layer.composite()
        bbox = layer.bbox
        
        # 标准化bbox
        try:
            # 新版可能是BBox对象
            left, top, right, bottom = bbox.x1, bbox.y1, bbox.x2, bbox.y2
        except AttributeError:
            # 旧版为tuple
            left, top, right, bottom = bbox
            
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        return img, (left, top, right, bottom)
    
    def _crop_part_with_view_mask(self, part_img: Image.Image, part_bbox: tuple, view_bbox: tuple, view_alpha: Image.Image) -> Image.Image:
        """用view的alpha通道裁剪part图层"""
        v_left, v_top, v_right, v_bottom = view_bbox
        v_w, v_h = v_right - v_left, v_bottom - v_top
        
        p_left, p_top, p_right, p_bottom = part_bbox
        dx, dy = p_left - v_left, p_top - v_top
        
        # 创建透明画布
        out = Image.new('RGBA', (v_w, v_h), (0, 0, 0, 0))
        
        # 计算相交区域
        part_alpha = part_img.split()[3]
        
        # 确保裁剪区域在范围内
        crop_left = max(0, dx)
        crop_top = max(0, dy)
        crop_right = min(v_w, dx + part_img.width)
        crop_bottom = min(v_h, dy + part_img.height)
        
        if crop_left >= crop_right or crop_top >= crop_bottom:
            return out  # 无相交区域
            
        # 对应的part图像区域
        part_crop_left = max(0, -dx)
        part_crop_top = max(0, -dy)
        part_crop_right = part_crop_left + (crop_right - crop_left)
        part_crop_bottom = part_crop_top + (crop_bottom - crop_top)
        
        # 裁剪view alpha对应区域
        mask_region = view_alpha.crop((crop_left, crop_top, crop_right, crop_bottom))
        
        # 裁剪part图像和alpha对应区域
        part_region = part_img.crop((part_crop_left, part_crop_top, part_crop_right, part_crop_bottom))
        part_alpha_region = part_alpha.crop((part_crop_left, part_crop_top, part_crop_right, part_crop_bottom))
        
        # 计算相交mask
        intersect_mask = ImageChops.multiply(part_alpha_region, mask_region)
        
        # 粘贴到输出画布
        out.paste(part_region, (crop_left, crop_top), mask=intersect_mask)
        return out
    
    def _build_layered_psd(self, output_path: str, canvas_size: tuple, layer_images: Dict[str, Image.Image]) -> bool:
        """构建分层PSD文件"""
        if not PYTOSHOP_AVAILABLE:
            print("[ERROR] pytoshop未安装，无法生成PSD")
            return False
            
        try:
            width, height = canvas_size
            layers = []
            
            # 按指定顺序处理图层
            order = ["view", "part1", "part2", "part3", "part4"]
            for name in order:
                pil_img = layer_images.get(name)
                if pil_img is None:
                    continue
                    
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')
                    
                # 确保尺寸与画布一致
                if pil_img.size != (width, height):
                    pil_img = pil_img.copy().resize((width, height), Image.NEAREST)
                
                r, g, b, a = pil_img.split()
                r_arr = np.array(r, dtype=np.uint8)
                g_arr = np.array(g, dtype=np.uint8)
                b_arr = np.array(b, dtype=np.uint8)
                a_arr = np.array(a, dtype=np.uint8)
                
                ch = {
                    0: r_arr,   # R
                    1: g_arr,   # G
                    2: b_arr,   # B
                    -1: a_arr,  # Alpha
                }
                
                lyr = nl.Image(
                    name=name,
                    top=0,
                    left=0,
                    bottom=height,
                    right=width,
                    channels=ch,
                    color_mode=nl.enums.ColorMode.rgb,
                    visible=True,
                    opacity=255,
                )
                layers.append(lyr)
            
            # 生成PSD文件
            psdfile = nl.nested_layers_to_psd(
                layers=layers,
                color_mode=nl.enums.ColorMode.rgb,
                size=(width, height),
                compression=nl.enums.Compression.raw,
            )
            
            with open(output_path, 'wb') as f:
                psdfile.write(f)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 构建PSD失败: {e}")
            import traceback
            traceback.print_exc()
            return False