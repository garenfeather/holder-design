#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
"""PSD缩放功能模块 - 集成自scripts/full_scale.py"""

import os
import glob
import shutil
import tempfile
from PIL import Image
from psd_tools import PSDImage
from utils.strings import sanitize_name
from psd_tools.api.psd_image import PSDImage as PSDImageAPI
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import Compression


class PSDScaler:
    """PSD缩放处理器"""
    
    def __init__(self):
        pass
    
    def _clean_layer_name(self, layer_name):
        """清理图层名称：先统一过滤不可见字符，再处理文件名非法字符"""
        clean_name = sanitize_name(layer_name)
        # 去除文件名中的非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            clean_name = clean_name.replace(char, '_')
        return clean_name.strip() or "unnamed_layer"
    
    def extract_layers_from_psd(self, psd_path: str, output_dir: str) -> bool:
        """
        从PSD文件中提取指定图层并保存为PNG文件
        
        Args:
            psd_path (str): 输入PSD文件路径
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not os.path.exists(psd_path):
            print(f"[ERROR] PSD文件不存在: {psd_path}")
            return False

        try:
            psd = PSDImage.open(psd_path)
            
            print(f"📂 打开PSD文件: {psd_path}")
            print(f"📐 PSD尺寸: {psd.width}x{psd.height}")
            
            if len(psd) == 0:
                print("[WARNING] 未找到图层")
                return False

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            for layer in psd:
                # 清理图层名称，去除空字节和其他问题字符
                clean_layer_name = self._clean_layer_name(layer.name)
                print(f"[SEARCH] 处理图层: '{clean_layer_name}'")
                output_filename = os.path.join(output_dir, f"{clean_layer_name}.png")
                    
                # 手动合成以确保画布尺寸保持
                layer_image = layer.topil()
                if layer_image is None:
                    print(f"[SKIP] 跳过图层 '{clean_layer_name}' (无像素数据)")
                    continue

                # 创建全尺寸透明画布
                full_size_canvas = Image.new('RGBA', (psd.width, psd.height), (0, 0, 0, 0))
                    
                # 将图层图像粘贴到正确位置
                full_size_canvas.paste(layer_image, (layer.left, layer.top))
                    
                # 保存结果
                full_size_canvas.save(output_filename)
                print(f"[SAVE] 保存 '{clean_layer_name}' 到 '{output_filename}'")

            print(f"[SUCCESS] 图层提取完成: {output_dir}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 提取图层时发生错误: {e}")
            return False

    def resize_png_dir(self, input_dir: str, output_dir: str, width: int, height: int) -> bool:
        """
        将目录下所有PNG文件统一缩放到指定尺寸
        
        Args:
            input_dir (str): 输入目录
            output_dir (str): 输出目录
            width (int): 目标宽度
            height (int): 目标高度
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            input_dir = os.path.abspath(input_dir)
            output_dir = os.path.abspath(output_dir)
            os.makedirs(output_dir, exist_ok=True)

            # 查找PNG文件
            pngs = sorted(glob.glob(os.path.join(input_dir, "*.png")) +
                          glob.glob(os.path.join(input_dir, "*.PNG")))
            
            if not pngs:
                print(f"[ERROR] 在目录中未找到PNG文件: {input_dir}")
                return False

            print(f"[SEARCH] 找到 {len(pngs)} 个PNG文件，目标尺寸: {width}x{height}")
            
            for i, src in enumerate(pngs, 1):
                name = os.path.basename(src)
                dst = os.path.join(output_dir, name)

                im = Image.open(src)
                # 保留透明通道
                if im.mode != "RGBA":
                    im = im.convert("RGBA")

                # 直接缩放到目标尺寸（强制不保持比例）
                im_resized = im.resize((width, height), Image.LANCZOS)

                # 保存（优化体积）
                im_resized.save(dst, optimize=True)
                print(f"📏 [{i}/{len(pngs)}] {name} -> {width}x{height}")

            print(f"[SUCCESS] 缩放完成: {output_dir}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 缩放PNG文件时发生错误: {e}")
            return False

    def create_psd_from_dir(self, input_dir: str, output_psd: str) -> bool:
        """
        从PNG文件目录创建PSD文件
        
        Args:
            input_dir (str): 输入目录路径
            output_psd (str): 输出PSD文件路径
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 获取目录下所有PNG文件
            png_files = sorted(glob.glob(os.path.join(input_dir, "*.png")))
            if not png_files:
                print(f"[ERROR] 在目录中未找到PNG文件: {input_dir}")
                return False

            # 获取第一个图片的尺寸作为PSD画布尺寸
            base = Image.open(png_files[0]).convert("RGBA")
            w, h = base.size
            print(f"📐 创建PSD，尺寸: {w}x{h}")

            # 创建新的PSD
            psd = PSDImageAPI.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))

            for p in png_files:
                name = os.path.splitext(os.path.basename(p))[0]
                print(f"📝 添加图层: {name}")
                im = Image.open(p).convert("RGBA")

                # 确保图片尺寸匹配
                if im.size != (w, h):
                    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                    canvas.paste(im, (0, 0))
                    im = canvas

                # 创建PSD图层
                layer = PixelLayer.frompil(
                    im,
                    psd_file=psd,
                    layer_name=name,
                    top=0,
                    left=0,
                    compression=Compression.RLE,
                )
                psd.append(layer)

            # 保存PSD文件
            psd.save(output_psd)
            print(f"[SAVE] 保存PSD: {output_psd}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 创建PSD文件时发生错误: {e}")
            return False

    def clear_temp_dir(self, path: str):
        """删除临时目录及其内容"""
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"🧹 删除临时目录: {path}")
        else:
            print(f"[WARNING] 目录不存在，跳过: {path}")

    def scale_psd(self, input_psd: str, output_psd: str, width: int, height: int) -> bool:
        """
        完整的PSD缩放流程
        
        Args:
            input_psd (str): 输入PSD文件路径
            output_psd (str): 输出PSD文件路径
            width (int): 目标宽度
            height (int): 目标高度
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        print(f"[START] 开始PSD缩放流程:")
        print(f"   输入: {input_psd}")
        print(f"   输出: {output_psd}")
        print(f"   目标尺寸: {width}x{height}")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory(prefix="psd_scale_") as temp_base:
            layers_dir = os.path.join(temp_base, "layers")
            resized_dir = os.path.join(temp_base, "resized")
            
            try:
                # 步骤1: 提取图层
                print(f"\n[STEP1] 提取图层...")
                if not self.extract_layers_from_psd(input_psd, layers_dir):
                    return False
                
                # 步骤2: 缩放图层
                print(f"\n[STEP2] 缩放图层...")
                if not self.resize_png_dir(layers_dir, resized_dir, width, height):
                    return False
                
                # 步骤3: 创建新PSD
                print(f"\n[STEP3] 创建新PSD...")
                if not self.create_psd_from_dir(resized_dir, output_psd):
                    return False
                
                print(f"\n[SUCCESS] PSD缩放完成: {output_psd}")
                return True
                
            except Exception as e:
                print(f"[ERROR] PSD缩放流程失败: {e}")
                return False
