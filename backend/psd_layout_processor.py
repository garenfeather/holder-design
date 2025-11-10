#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PSD 布局处理器
功能：从原始PSD提取每个图层的可见像素区域，填充白色后生成新PSD
参考：psd_cropper.py 的实现模式
"""

from typing import List, Dict, Tuple
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage

try:
    from pytoshop.user import nested_layers as nl
    import numpy as np
    PYTOSHOP_AVAILABLE = True
except Exception:
    PYTOSHOP_AVAILABLE = False


class PSDLayoutProcessor:
    """PSD布局处理器类"""

    def __init__(self):
        pass

    def create_white_filled_layout_psd(self, input_psd_path: str, output_psd_path: str) -> bool:
        """
        从原始PSD提取每个图层的可见像素区域，填充白色后生成新PSD

        Args:
            input_psd_path: 输入PSD文件路径
            output_psd_path: 输出PSD文件路径

        Returns:
            是否成功
        """
        try:
            print("=" * 60)
            print("🎨 PSD布局处理器 - 白色填充模式")
            print("=" * 60)
            print(f"📂 输入: {input_psd_path}")
            print(f"📂 输出: {output_psd_path}")

            # 1. 加载PSD
            psd = PSDImage.open(input_psd_path)
            canvas_width = psd.width
            canvas_height = psd.height

            print(f"📐 画布尺寸: {canvas_width} × {canvas_height} 像素")

            # 2. 提取所有图层并处理
            processed_layers = []
            layer_count = 0

            for layer in psd.descendants():
                # 跳过组
                if layer.is_group():
                    continue

                layer_count += 1
                layer_name = layer.name

                # 获取图层的合成图像和边界框
                layer_img = layer.composite()
                bbox = layer.bbox

                # 标准化bbox
                try:
                    left, top, right, bottom = bbox.x1, bbox.y1, bbox.x2, bbox.y2
                except AttributeError:
                    left, top, right, bottom = bbox

                # 白色填充处理
                white_filled_img = self._fill_visible_with_white(layer_img)

                processed_layers.append({
                    'name': layer_name,
                    'image': white_filled_img,
                    'bbox': (left, top, right, bottom)
                })

                print(f"  ✓ 处理图层 {layer_count}: {layer_name}")

            print(f"\n📊 共处理 {len(processed_layers)} 个图层")

            # 3. 构建新PSD
            if not PYTOSHOP_AVAILABLE:
                print("❌ pytoshop 未安装，无法生成PSD")
                return False

            success = self._build_psd_from_layers(
                output_path=output_psd_path,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                layers=processed_layers
            )

            if success:
                print(f"✅ 布局PSD生成成功: {output_psd_path}")
                return True
            else:
                print("❌ PSD生成失败")
                return False

        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _fill_visible_with_white(self, img: Image.Image) -> Image.Image:
        """
        将图像的可见像素填充为白色，保持alpha通道不变

        Args:
            img: 输入图像

        Returns:
            填充后的图像
        """
        # 确保是RGBA模式
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 创建副本避免修改原图
        img = img.copy()

        # 获取像素访问对象
        pixels = img.load()

        # 遍历所有像素
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                # 如果像素可见(alpha > 0)，填充为白色
                if a > 0:
                    pixels[x, y] = (255, 255, 255, a)

        return img

    def _build_psd_from_layers(self, output_path: str, canvas_width: int,
                               canvas_height: int, layers: List[Dict]) -> bool:
        """
        使用pytoshop构建PSD文件（参考psd_cropper.py的实现）

        Args:
            output_path: 输出文件路径
            canvas_width: 画布宽度
            canvas_height: 画布高度
            layers: 图层列表，每个元素包含 {'name', 'image', 'bbox'}

        Returns:
            是否成功
        """
        try:
            psd_layers = []

            for layer_data in layers:
                layer_name = layer_data['name']
                layer_img = layer_data['image']
                left, top, right, bottom = layer_data['bbox']

                # 创建完整画布大小的透明图像
                canvas_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

                # 将图层图像粘贴到对应位置
                canvas_img.paste(layer_img, (left, top))

                # 确保是RGBA模式
                if canvas_img.mode != 'RGBA':
                    canvas_img = canvas_img.convert('RGBA')

                # 分离通道并转换为numpy数组
                r, g, b, a = canvas_img.split()
                r_arr = np.array(r, dtype=np.uint8)
                g_arr = np.array(g, dtype=np.uint8)
                b_arr = np.array(b, dtype=np.uint8)
                a_arr = np.array(a, dtype=np.uint8)

                # 构建通道字典
                channels = {
                    0: r_arr,   # Red
                    1: g_arr,   # Green
                    2: b_arr,   # Blue
                    -1: a_arr,  # Alpha
                }

                # 创建pytoshop图层对象
                psd_layer = nl.Image(
                    name=layer_name,
                    top=0,
                    left=0,
                    bottom=canvas_height,
                    right=canvas_width,
                    channels=channels,
                    color_mode=nl.enums.ColorMode.rgb,
                    visible=True,
                    opacity=255,
                )

                psd_layers.append(psd_layer)

            # 生成PSD文件
            psdfile = nl.nested_layers_to_psd(
                layers=psd_layers,
                color_mode=nl.enums.ColorMode.rgb,
                size=(canvas_width, canvas_height),
                compression=nl.enums.Compression.raw,
            )

            # 设置分辨率为 300 DPI
            # Resolution Info 的格式：horizontal_res(4字节), h_res_unit(2字节), width_unit(2字节),
            #                        vertical_res(4字节), v_res_unit(2字节), height_unit(2字节)
            from config import processing_config
            import struct
            from pytoshop.image_resources import GenericImageResourceBlock

            dpi = processing_config.DIE_ELEMENT_DEFAULT_DPI
            # DPI 需要转换为 Fixed point: dpi * 65536
            h_res = int(dpi * 65536)
            v_res = int(dpi * 65536)

            # 构建 Resolution Info 数据
            # h_res_unit: 1 = pixels per inch, width_unit: 2 = inches
            # v_res_unit: 1 = pixels per inch, height_unit: 2 = inches
            res_data = struct.pack('>IHH IHH', h_res, 1, 2, v_res, 1, 2)

            # 创建 Resolution Info block (Resource ID = 1005)
            res_block = GenericImageResourceBlock(resource_id=1005, name='', data=res_data)

            # 添加到 image_resources
            psdfile.image_resources._blocks.append(res_block)

            # 写入文件
            with open(output_path, 'wb') as f:
                psdfile.write(f)

            return True

        except Exception as e:
            print(f"❌ 构建PSD失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 全局实例
psd_layout_processor = PSDLayoutProcessor()
