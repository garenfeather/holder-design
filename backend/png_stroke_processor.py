#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
"""PNG描边处理器 - 复现png_edge_stroke.py的描边逻辑"""

# 标准库导入
import sys
from pathlib import Path

# 第三方库导入
from PIL import Image, ImageFilter, ImageChops

# 本地模块导入
from config import processing_config

# 尝试导入numpy和scipy，如果失败则使用备用算法
try:
    import numpy as np
    from scipy import ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class PNGStrokeProcessor:
    """PNG描边处理器

    复现scripts/png_edge_stroke.py的核心描边逻辑，
    支持scipy高级算法和PIL备用算法，具备UTF-8字符支持。
    """

    def __init__(self, stroke_width=None, stroke_color=None, smooth_factor=None):
        """
        初始化PNG描边处理器

        Args:
            stroke_width (int): 描边宽度（像素）
            stroke_color (tuple): 描边颜色 (R, G, B, A)
            smooth_factor (float): 光滑因子，越大越平滑
        """
        self.stroke_width = stroke_width or processing_config.DEFAULT_STROKE_WIDTH
        self.stroke_color = stroke_color or processing_config.DEFAULT_STROKE_COLOR
        self.smooth_factor = smooth_factor or processing_config.DEFAULT_STROKE_SMOOTH_FACTOR

    def _has_scipy(self):
        """检测scipy可用性"""
        return HAS_SCIPY

    def _validate_image(self, image):
        """验证输入图像"""
        if not isinstance(image, Image.Image):
            raise ValueError("输入必须是PIL Image对象")

        # 确保是RGBA模式
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # 检查是否有有效像素
        alpha = image.split()[3]
        valid_pixels = sum(1 for pixel in alpha.getdata() if pixel > 0)

        if valid_pixels == 0:
            raise ValueError("图像中没有可见像素（完全透明）")

        return image

    def _create_smooth_stroke_scipy(self, image):
        """使用scipy创建光滑描边蒙版（高级算法）"""
        # 提取alpha通道并转换为numpy数组
        alpha = image.split()[3]
        alpha_array = np.array(alpha, dtype=np.float32) / 255.0

        # 创建二值化蒙版
        binary_mask = (alpha_array > 0).astype(np.float32)

        # 使用距离变换创建平滑的扩展
        # 首先对蒙版进行轻微的高斯模糊，增加边缘的平滑度
        smooth_kernel_size = max(1, int(self.stroke_width * self.smooth_factor * 0.5))
        if smooth_kernel_size > 0:
            binary_mask = ndimage.gaussian_filter(binary_mask, sigma=smooth_kernel_size)

        # 创建距离变换
        # 对于外侧描边，我们需要计算从边缘向外的距离
        # 首先反转蒙版：背景为True，前景为False
        inverted_mask = (binary_mask < 0.5)
        distance_transform = ndimage.distance_transform_edt(inverted_mask)

        # 创建描边区域：距离小于等于描边宽度的区域
        stroke_mask = (distance_transform <= self.stroke_width).astype(np.float32)

        # 应用高斯模糊使描边更加平滑
        blur_sigma = self.stroke_width * self.smooth_factor * 0.3
        if blur_sigma > 0:
            stroke_mask = ndimage.gaussian_filter(stroke_mask, sigma=blur_sigma)

        # 从描边蒙版中减去原始蒙版，得到纯外侧描边
        original_mask_smooth = ndimage.gaussian_filter(binary_mask, sigma=0.5)
        pure_stroke_mask = np.maximum(0, stroke_mask - original_mask_smooth)

        # 确保描边强度在合理范围内
        pure_stroke_mask = np.clip(pure_stroke_mask, 0, 1)

        # 转换回PIL图像
        stroke_alpha = (pure_stroke_mask * 255).astype(np.uint8)
        return Image.fromarray(stroke_alpha).convert('L')

    def _create_smooth_stroke_pil(self, image):
        """使用PIL创建描边蒙版（备用算法）"""
        # 提取alpha通道
        alpha = image.split()[3]

        # 创建多重膨胀以获得更平滑的描边
        stroke_mask = alpha.copy()

        # 多次应用MaxFilter以创建平滑的扩展
        kernel_size = 3
        iterations = max(1, self.stroke_width)

        for i in range(iterations):
            stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(kernel_size))

        # 应用高斯模糊增加平滑度
        blur_radius = max(0.5, self.stroke_width * self.smooth_factor * 0.5)
        stroke_mask = stroke_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # 从描边蒙版中减去原始蒙版
        return ImageChops.subtract(stroke_mask, alpha)

    def _apply_stroke_color(self, image, stroke_mask):
        """应用描边颜色并合成结果"""
        # 创建结果画布
        result = Image.new('RGBA', image.size, (0, 0, 0, 0))

        # 将stroke_mask转换为二值蒙版（确保100%不透明度）
        # 任何大于阈值的像素都设为完全不透明的描边颜色
        stroke_threshold = 10  # 阈值，避免噪声

        # 遍历每个像素，应用纯白色描边
        result_pixels = []
        stroke_pixels = list(stroke_mask.getdata())

        for i, mask_value in enumerate(stroke_pixels):
            if mask_value > stroke_threshold:
                # 描边区域：纯白色100%不透明
                result_pixels.append(self.stroke_color)
            else:
                # 非描边区域：透明
                result_pixels.append((0, 0, 0, 0))

        result.putdata(result_pixels)

        # 然后放置原图案（在顶层），保持原图案的透明度
        result.paste(image, (0, 0), image)

        return result

    def process_png(self, image_input):
        """
        对PNG图像进行描边处理

        Args:
            image_input: PIL Image对象或文件路径

        Returns:
            PIL Image对象: 描边处理后的图像

        Raises:
            ValueError: 输入验证失败
            Exception: 处理过程中的其他错误
        """
        try:
            # 处理输入
            if isinstance(image_input, (str, Path)):
                # 文件路径输入，使用UTF-8安全处理
                input_path_safe = str(image_input).encode('utf-8').decode('utf-8')
                image = Image.open(input_path_safe).convert('RGBA')
            else:
                image = image_input

            # 验证图像
            image = self._validate_image(image)

            # 创建描边蒙版
            if self._has_scipy():
                stroke_mask = self._create_smooth_stroke_scipy(image)
            else:
                stroke_mask = self._create_smooth_stroke_pil(image)

            # 应用描边颜色并合成
            result = self._apply_stroke_color(image, stroke_mask)

            return result

        except Exception as e:
            # 确保错误信息的UTF-8编码安全
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            raise Exception(f"PNG描边处理失败: {error_msg}")

    def process_png_file(self, input_path, output_path):
        """
        处理PNG文件并保存结果

        Args:
            input_path (str): 输入文件路径
            output_path (str): 输出文件路径

        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 处理图像
            result = self.process_png(input_path)

            # 保存结果
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用UTF-8安全的路径保存
            output_path_safe = str(output_path).encode('utf-8').decode('utf-8')
            result.save(output_path_safe, 'PNG', optimize=True)

            return True

        except Exception as e:
            # 确保错误信息的UTF-8编码安全
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"[ERROR] PNG文件描边处理失败: {error_msg}")
            return False

    def get_algorithm_info(self):
        """获取当前使用的算法信息"""
        if self._has_scipy():
            return {
                "algorithm": "scipy_advanced",
                "description": "距离变换 + 高斯模糊高级算法",
                "dependencies": ["numpy", "scipy"]
            }
        else:
            return {
                "algorithm": "pil_fallback",
                "description": "PIL形态学操作备用算法",
                "dependencies": ["PIL"]
            }


def create_stroke_processor(stroke_width=None, stroke_color=None, smooth_factor=None):
    """
    工厂函数：创建PNG描边处理器实例

    Args:
        stroke_width (int): 描边宽度（像素）
        stroke_color (tuple): 描边颜色 (R, G, B, A)
        smooth_factor (float): 光滑因子

    Returns:
        PNGStrokeProcessor: 描边处理器实例
    """
    return PNGStrokeProcessor(stroke_width, stroke_color, smooth_factor)


# 兼容性函数：与原脚本保持一致的接口
def process_png_stroke(input_image, stroke_width=None, stroke_color=None):
    """
    兼容性函数：简化的PNG描边接口

    Args:
        input_image: PIL Image对象或文件路径
        stroke_width (int): 描边宽度
        stroke_color (tuple): 描边颜色

    Returns:
        PIL Image对象: 描边处理后的图像
    """
    processor = PNGStrokeProcessor(stroke_width, stroke_color)
    return processor.process_png(input_image)


if __name__ == "__main__":
    # 简单的测试代码
    import sys

    if len(sys.argv) < 2:
        print("用法: python png_stroke_processor.py <input_png> [output_png] [stroke_width]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    stroke_width = int(sys.argv[3]) if len(sys.argv) > 3 else processing_config.DEFAULT_STROKE_WIDTH

    if not output_path:
        input_p = Path(input_path)
        output_path = input_p.parent / f"{input_p.stem}_stroke{input_p.suffix}"

    processor = PNGStrokeProcessor(stroke_width=stroke_width)
    success = processor.process_png_file(input_path, output_path)

    if success:
        print(f"✅ 描边完成: {output_path}")
    else:
        print("❌ 描边失败")
        sys.exit(1)