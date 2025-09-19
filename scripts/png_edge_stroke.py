#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
# 确保UTF-8编码支持
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

"""
PNG图案边缘描边工具

功能：对PNG图案的实际像素边缘进行光滑外侧描边
特点：
- 外侧描边：描边不会覆盖原始图案
- 光滑模式：使用高斯模糊和距离变换创建平滑描边
- 像素级精度：针对图案的实际像素边缘，非图像边框
- 可配置参数：描边宽度、颜色、透明度

用法：
    python png_edge_stroke.py input.png [options]

示例：
    python png_edge_stroke.py logo.png --stroke-width 3 --stroke-color 255,255,255,255
    python png_edge_stroke.py icon.png -w 5 -c 0,0,0,200 -o result.png

算法：
1. 提取PNG图案的alpha通道作为蒙版
2. 使用距离变换和高斯模糊创建光滑的描边区域
3. 从描边区域中减去原始图案区域，得到纯外侧描边
4. 应用描边颜色并与原图案合成
5. 输出带描边的结果图像
"""

from PIL import Image, ImageFilter, ImageChops, ImageDraw
from pathlib import Path
import sys
import argparse

# 尝试导入numpy和scipy，如果失败则使用备用算法
try:
    import numpy as np
    from scipy import ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class PNGEdgeStroker:
    def __init__(self, input_path, output_path=None, stroke_width=2,
                 stroke_color=(255, 255, 255, 255), smooth_factor=1.0):
        """
        初始化PNG边缘描边器

        Args:
            input_path: 输入PNG文件路径
            output_path: 输出文件路径，如果为None则自动生成
            stroke_width: 描边宽度（像素）
            stroke_color: 描边颜色 (R, G, B, A)
            smooth_factor: 光滑因子，越大越平滑
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self._generate_output_path()
        self.stroke_width = stroke_width
        self.stroke_color = stroke_color
        self.smooth_factor = smooth_factor

    def _generate_output_path(self):
        """生成输出文件路径"""
        stem = self.input_path.stem
        suffix = self.input_path.suffix
        return self.input_path.parent / f"{stem}_stroke{suffix}"

    def validate_input(self):
        """验证输入文件"""
        print(f"📂 验证输入文件...")

        if not self.input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {self.input_path}")

        print(f"  ✓ 输入文件: {self.input_path.name}")

        # 加载并验证图像
        try:
            # 使用UTF-8安全的路径处理
            input_path_safe = str(self.input_path).encode('utf-8').decode('utf-8')
            self.image = Image.open(input_path_safe).convert('RGBA')
            print(f"  ✓ 图像尺寸: {self.image.size[0]}×{self.image.size[1]} px")
        except Exception as e:
            raise ValueError(f"无法加载图像文件: {e}")

        # 检查是否有透明通道和有效像素
        alpha = self.image.split()[3]
        valid_pixels = sum(1 for pixel in alpha.getdata() if pixel > 0)
        total_pixels = self.image.size[0] * self.image.size[1]

        if valid_pixels == 0:
            raise ValueError("图像中没有可见像素（完全透明）")

        print(f"  ✓ 有效像素: {valid_pixels:,} / {total_pixels:,} ({valid_pixels/total_pixels*100:.1f}%)")
        return True

    def analyze_edge_complexity(self):
        """分析图案边缘复杂度"""
        print(f"\n📊 分析图案边缘...")

        # 提取alpha通道
        alpha = self.image.split()[3]

        if HAS_SCIPY:
            alpha_array = np.array(alpha)
            # 创建二值化蒙版
            mask = (alpha_array > 0).astype(np.uint8)
            # 计算边缘像素数量
            # 使用Sobel算子检测边缘
            edge_x = ndimage.sobel(mask, axis=0)
            edge_y = ndimage.sobel(mask, axis=1)
            edge_magnitude = np.sqrt(edge_x**2 + edge_y**2)
            edge_pixels = np.sum(edge_magnitude > 0)
        else:
            # 简单的边缘检测：统计有alpha值的像素
            edge_pixels = sum(1 for pixel in alpha.getdata() if pixel > 0)

        self.edge_complexity = edge_pixels

        print(f"  图案边缘长度: {edge_pixels:,} 像素")
        print(f"  描边宽度: {self.stroke_width} 像素")
        print(f"  光滑因子: {self.smooth_factor}")
        print(f"  描边颜色: RGBA{self.stroke_color}")

        return True

    def create_smooth_stroke_mask(self):
        """创建光滑的描边蒙版"""
        print(f"\n🎨 生成光滑描边蒙版...")

        # 提取alpha通道并转换为numpy数组
        alpha = self.image.split()[3]
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
        self.stroke_mask = Image.fromarray(stroke_alpha, 'L')

        # 统计描边像素
        stroke_pixels = np.sum(pure_stroke_mask > 0.1)  # 阈值0.1避免噪声
        print(f"  ✓ 描边像素数量: {stroke_pixels:,}")
        print(f"  ✓ 描边/原图比例: {stroke_pixels/np.sum(binary_mask > 0.5):.2f}")

        return True

    def create_stroke_fallback(self):
        """备用描边算法（基于PIL的膨胀操作）"""
        print(f"  使用备用描边算法...")

        # 提取alpha通道
        alpha = self.image.split()[3]

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
        self.stroke_mask = ImageChops.subtract(stroke_mask, alpha)

        stroke_pixels = sum(1 for pixel in self.stroke_mask.getdata() if pixel > 10)
        print(f"  ✓ 备用算法描边像素: {stroke_pixels:,}")

        return True

    def apply_stroke_color(self):
        """应用描边颜色"""
        print(f"\n🎯 应用描边颜色...")

        # 创建描边图层
        stroke_layer = Image.new('RGBA', self.image.size, self.stroke_color)

        # 创建结果画布
        self.result = Image.new('RGBA', self.image.size, (0, 0, 0, 0))

        # 首先放置描边（在底层）
        self.result.paste(stroke_layer, (0, 0), self.stroke_mask)

        # 然后放置原图案（在顶层）
        self.result.paste(self.image, (0, 0), self.image)

        # 统计最终结果
        final_pixels = sum(1 for pixel in self.result.getdata() if pixel[3] > 0)
        original_pixels = sum(1 for pixel in self.image.getdata() if pixel[3] > 0)
        added_pixels = final_pixels - original_pixels

        print(f"  ✓ 原始像素: {original_pixels:,}")
        print(f"  ✓ 最终像素: {final_pixels:,}")
        print(f"  ✓ 新增描边: {added_pixels:,}")

        return True

    def save_result(self):
        """保存处理结果"""
        print(f"\n💾 保存结果...")

        try:
            # 确保输出目录存在
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图像 - 使用UTF-8安全的路径
            output_path_safe = str(self.output_path).encode('utf-8').decode('utf-8')
            self.result.save(output_path_safe, 'PNG', optimize=True)

            # 验证文件
            if self.output_path.exists():
                file_size = self.output_path.stat().st_size
                print(f"  ✓ 已保存到: {self.output_path}")
                print(f"  ✓ 文件大小: {file_size:,} bytes")
                return True
            else:
                raise Exception("文件保存失败")

        except Exception as e:
            # 确保错误信息的UTF-8编码安全
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"  ❌ 保存失败: {error_msg}")
            return False

    def process(self):
        """执行完整的描边流程"""
        try:
            print("=" * 60)
            print("🎨 PNG图案边缘描边工具")
            print("=" * 60)

            # 1. 验证输入
            if not self.validate_input():
                return False

            # 2. 分析边缘
            if not self.analyze_edge_complexity():
                return False

            # 3. 创建描边蒙版
            if HAS_SCIPY:
                if not self.create_smooth_stroke_mask():
                    return False
            else:
                print("  ⚠️ numpy/scipy未安装，使用备用算法")
                if not self.create_stroke_fallback():
                    return False

            # 4. 应用颜色
            if not self.apply_stroke_color():
                return False

            # 5. 保存结果
            if not self.save_result():
                return False

            print("\n" + "=" * 60)
            print("✅ 描边完成!")
            print(f"📁 输入文件: {self.input_path.name}")
            print(f"📁 输出文件: {self.output_path.name}")
            print(f"📐 图像尺寸: {self.image.size[0]}×{self.image.size[1]} px")
            print(f"🎨 描边宽度: {self.stroke_width} px")
            print(f"🎨 描边颜色: RGBA{self.stroke_color}")
            print(f"✨ 光滑因子: {self.smooth_factor}")
            print("=" * 60)

            return True

        except Exception as e:
            # 确保错误信息的UTF-8编码安全
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"❌ 处理失败: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def parse_color(color_str):
    """解析颜色字符串"""
    try:
        if ',' in color_str:
            parts = [int(x.strip()) for x in color_str.split(',')]
            if len(parts) == 3:
                return tuple(parts + [255])  # 添加默认alpha
            elif len(parts) == 4:
                return tuple(parts)
            else:
                raise ValueError("颜色格式错误")
        else:
            # 十六进制颜色
            if color_str.startswith('#'):
                color_str = color_str[1:]
            if len(color_str) == 6:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                return (r, g, b, 255)
            elif len(color_str) == 8:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                a = int(color_str[6:8], 16)
                return (r, g, b, a)
            else:
                raise ValueError("十六进制颜色格式错误")
    except Exception:
        raise ValueError(f"无法解析颜色: {color_str}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PNG图案边缘描边工具 - 对PNG图案进行光滑外侧描边',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s logo.png --stroke-width 3
  %(prog)s icon.png -w 5 -c 255,0,0,200 -o result.png
  %(prog)s pattern.png --stroke-color "#FF0000" --smooth 1.5

颜色格式:
  - RGB: "255,0,0" (红色)
  - RGBA: "255,0,0,128" (半透明红色)
  - 十六进制: "#FF0000" 或 "#FF000080"
        """
    )

    parser.add_argument('input', help='输入PNG文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('-w', '--stroke-width', type=int, default=2,
                       help='描边宽度，单位像素（默认: 2）')
    parser.add_argument('-c', '--stroke-color', default='255,255,255,255',
                       help='描边颜色，格式: R,G,B,A 或 #RRGGBB（默认: 白色）')
    parser.add_argument('-s', '--smooth', type=float, default=1.0,
                       help='光滑因子，越大越平滑（默认: 1.0）')

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    try:
        args = parser.parse_args()

        # 检查输入文件 - 使用UTF-8安全处理
        input_path = args.input.encode('utf-8').decode('utf-8') if isinstance(args.input, str) else str(args.input)
        if not Path(input_path).exists():
            print(f"❌ 输入文件不存在: {input_path}")
            return 1

        # 解析颜色
        try:
            stroke_color = parse_color(args.stroke_color)
        except ValueError as e:
            print(f"❌ {e}")
            return 1

        # 验证参数
        if args.stroke_width <= 0:
            print("❌ 描边宽度必须大于0")
            return 1

        if args.smooth <= 0:
            print("❌ 光滑因子必须大于0")
            return 1

        # 处理输出路径的UTF-8编码
        output_path = None
        if args.output:
            output_path = args.output.encode('utf-8').decode('utf-8') if isinstance(args.output, str) else str(args.output)

        # 创建描边器
        stroker = PNGEdgeStroker(
            input_path=input_path,
            output_path=output_path,
            stroke_width=args.stroke_width,
            stroke_color=stroke_color,
            smooth_factor=args.smooth
        )

        # 执行描边
        success = stroker.process()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        return 1
    except Exception as e:
        # 确保错误信息的UTF-8编码安全
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"❌ 程序执行失败: {error_msg}")
        import traceback
        traceback.print_exc()
        return 1


# 备用的简化版本（不依赖numpy/scipy）
def create_simple_stroke_mask(image, stroke_width, smooth_factor):
    """简化版描边蒙版创建（仅使用PIL）"""
    alpha = image.split()[3]

    # 多次膨胀
    stroke_mask = alpha.copy()
    for i in range(stroke_width):
        stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(3))

    # 高斯模糊
    blur_radius = stroke_width * smooth_factor * 0.5
    if blur_radius > 0:
        stroke_mask = stroke_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # 减去原始图案
    stroke_only = ImageChops.subtract(stroke_mask, alpha)

    return stroke_only


if __name__ == "__main__":
    exit(main())