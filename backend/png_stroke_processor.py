#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
"""PNG描边处理器 - 精确像素描边实现"""

# 标准库导入
import sys
from pathlib import Path

# 第三方库导入
from PIL import Image, ImageFilter, ImageChops

# 本地模块导入
from config import processing_config


class PNGStrokeProcessor:
    """PNG描边处理器

    基于形态学的精确像素描边实现，完全替换原有的距离变换+高斯模糊算法。
    特点：
    - 精确像素控制：输入N像素，输出精确N像素描边
    - 基于形态学操作：使用MaxFilter逐层膨胀，避免连续值问题
    - 无模糊效应：边缘锐利清晰，不使用高斯模糊
    - 外侧描边：只在图案外部添加描边，不覆盖原始内容
    """

    def __init__(self, stroke_width=None, stroke_color=None, smooth_factor=None):
        """
        初始化PNG描边处理器

        Args:
            stroke_width (int): 描边宽度（像素）
            stroke_color (tuple): 描边颜色 (R, G, B, A)
            smooth_factor (float): 兼容性参数，在新算法中不使用
        """
        self.stroke_width = stroke_width or processing_config.DEFAULT_STROKE_WIDTH
        self.stroke_color = stroke_color or processing_config.DEFAULT_STROKE_COLOR
        # smooth_factor在精确算法中不需要，保留只为向后兼容
        self.smooth_factor = smooth_factor or processing_config.DEFAULT_STROKE_SMOOTH_FACTOR

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

    def _create_precise_stroke_mask(self, image):
        """创建精确的描边蒙版 - 基于形态学操作"""
        try:
            # 提取alpha通道并转换为严格的二值掩码
            alpha = image.split()[3]

            # 创建二值掩码：>0的像素设为255，其他为0
            binary_mask = alpha.point(lambda x: 255 if x > 0 else 0)

            # 使用形态学膨胀进行精确扩展
            # 每次膨胀恰好扩展1像素
            stroke_mask = binary_mask.copy()

            for i in range(self.stroke_width):
                # 使用3x3的MaxFilter进行1像素精确膨胀
                # MaxFilter会将每个像素替换为其3x3邻域内的最大值
                stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(3))

            # 从膨胀后的蒙版中减去原始蒙版，得到纯描边区域
            pure_stroke_mask = ImageChops.subtract(stroke_mask, binary_mask)

            return pure_stroke_mask

        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            raise Exception(f"创建描边蒙版失败: {error_msg}")

    def _apply_stroke_color_precise(self, image, stroke_mask):
        """应用描边颜色 - 精确合成"""
        try:
            # 创建描边图层
            stroke_layer = Image.new('RGBA', image.size, self.stroke_color)

            # 创建结果画布
            result = Image.new('RGBA', image.size, (0, 0, 0, 0))

            # 首先放置描边（底层）- 使用精确的二值蒙版
            result.paste(stroke_layer, (0, 0), stroke_mask)

            # 然后放置原图案（顶层）- 保持原始透明度
            result.paste(image, (0, 0), image)

            return result

        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            raise Exception(f"应用描边颜色失败: {error_msg}")

    def process_png(self, image_input):
        """
        对PNG图像进行精确描边处理

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

            # 创建精确描边蒙版
            stroke_mask = self._create_precise_stroke_mask(image)

            # 应用描边颜色并合成
            result = self._apply_stroke_color_precise(image, stroke_mask)

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
        return {
            "algorithm": "precise_morphology",
            "description": "基于形态学的精确像素描边",
            "dependencies": ["PIL"],
            "features": ["pixel_perfect", "no_blur", "outside_stroke"]
        }


def create_stroke_processor(stroke_width=None, stroke_color=None, smooth_factor=None):
    """
    工厂函数：创建PNG描边处理器实例

    Args:
        stroke_width (int): 描边宽度（像素）
        stroke_color (tuple): 描边颜色 (R, G, B, A)
        smooth_factor (float): 兼容性参数，在新算法中不使用

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
        output_path = input_p.parent / f"{input_p.stem}_precise_stroke{input_p.suffix}"

    processor = PNGStrokeProcessor(stroke_width=stroke_width)
    success = processor.process_png_file(input_path, output_path)

    if success:
        print(f"✅ 精确描边完成: {output_path}")
        print(f"📐 描边宽度: {stroke_width} 像素 (精确控制)")
        print(f"🔬 算法类型: {processor.get_algorithm_info()['description']}")
    else:
        print("❌ 描边失败")
        sys.exit(1)