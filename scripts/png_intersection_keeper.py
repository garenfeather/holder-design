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
PNG图层交集保留工具

功能：输入两个同尺寸的PNG文件A和B，计算它们的像素交集，
然后仅保留B中与A交集的像素部分（非交集部分设为透明）

用法：
    python png_intersection_keeper.py image_a.png image_b.png [output.png]

示例：
    python png_intersection_keeper.py layer1.png layer2.png result.png
    python png_intersection_keeper.py layer1.png layer2.png  # 自动生成输出文件名

算法：
1. 加载两个PNG文件并转换为RGBA格式
2. 验证尺寸是否一致
3. 逐像素检查交集：两个位置的alpha都>0的像素
4. 在B图像中仅保留交集位置的像素，其余位置设为透明
5. 保存处理后的结果
"""

from PIL import Image, ImageChops
from pathlib import Path
import sys


class PNGIntersectionKeeper:
    def __init__(self, png_a_path, png_b_path, output_path=None):
        """
        初始化PNG交集保留器

        Args:
            png_a_path: 参考图像A的路径
            png_b_path: 要处理的图像B的路径
            output_path: 输出文件路径，如果为None则自动生成
        """
        self.png_a_path = Path(png_a_path)
        self.png_b_path = Path(png_b_path)
        self.output_path = Path(output_path) if output_path else self._generate_output_path()

    def _generate_output_path(self):
        """生成输出文件路径"""
        stem = self.png_b_path.stem
        suffix = self.png_b_path.suffix
        return self.png_b_path.parent / f"{stem}_intersection_only{suffix}"

    def validate_inputs(self):
        """验证输入文件"""
        print(f"📂 验证输入文件...")

        # 检查文件存在
        if not self.png_a_path.exists():
            raise FileNotFoundError(f"图像A不存在: {self.png_a_path}")

        if not self.png_b_path.exists():
            raise FileNotFoundError(f"图像B不存在: {self.png_b_path}")

        print(f"  ✓ 图像A: {self.png_a_path.name}")
        print(f"  ✓ 图像B: {self.png_b_path.name}")

        # 加载并验证图像
        try:
            # 使用UTF-8安全的路径处理
            path_a = str(self.png_a_path).encode('utf-8').decode('utf-8')
            path_b = str(self.png_b_path).encode('utf-8').decode('utf-8')
            self.image_a = Image.open(path_a).convert('RGBA')
            self.image_b = Image.open(path_b).convert('RGBA')
        except Exception as e:
            raise ValueError(f"无法加载图像文件: {e}")

        # 验证尺寸匹配
        if self.image_a.size != self.image_b.size:
            raise ValueError(
                f"图像尺寸不匹配: "
                f"A={self.image_a.size[0]}×{self.image_a.size[1]}, "
                f"B={self.image_b.size[0]}×{self.image_b.size[1]}"
            )

        print(f"  ✓ 尺寸匹配: {self.image_a.size[0]}×{self.image_a.size[1]} px")
        return True

    def calculate_intersection_stats(self):
        """计算交集统计信息"""
        print(f"\n📊 分析像素交集...")

        # 提取alpha通道
        alpha_a = self.image_a.split()[3]
        alpha_b = self.image_b.split()[3]

        # 计算有效像素数量
        pixels_a = list(alpha_a.getdata())
        pixels_b = list(alpha_b.getdata())

        valid_a = sum(1 for alpha in pixels_a if alpha > 0)
        valid_b = sum(1 for alpha in pixels_b if alpha > 0)

        # 计算交集像素数量
        intersection_count = sum(
            1 for i in range(len(pixels_a))
            if pixels_a[i] > 0 and pixels_b[i] > 0
        )

        total_pixels = len(pixels_a)

        print(f"  图像A有效像素: {valid_a:,} / {total_pixels:,} ({valid_a/total_pixels*100:.1f}%)")
        print(f"  图像B有效像素: {valid_b:,} / {total_pixels:,} ({valid_b/total_pixels*100:.1f}%)")
        print(f"  交集像素数量: {intersection_count:,} / {total_pixels:,} ({intersection_count/total_pixels*100:.1f}%)")

        if intersection_count == 0:
            print(f"  ⚠️ 警告: 两个图像没有像素交集，结果将是完全透明的图像")

        return intersection_count

    def keep_intersection_optimized(self):
        """使用ImageChops优化的交集保留算法"""
        print(f"\n✂️ 保留交集像素...")

        # 提取各通道
        r_b, g_b, b_b, alpha_b = self.image_b.split()
        alpha_a = self.image_a.split()[3]

        # 计算交集蒙版：两个alpha通道的乘积（相当于逻辑AND操作）
        # 当两个alpha都>0时，乘积>0；否则为0
        intersection_mask = ImageChops.multiply(alpha_a, alpha_b)

        # 使用交集蒙版作为新的alpha通道
        # 这样只有交集部分保持原来的透明度，其他部分完全透明
        new_alpha_b = intersection_mask

        # 重新组合RGBA通道
        self.result_image = Image.merge('RGBA', (r_b, g_b, b_b, new_alpha_b))

        print(f"  ✓ 交集保留完成")
        return True

    def keep_intersection_precise(self):
        """精确的逐像素交集保留算法（备用方案）"""
        print(f"\n✂️ 保留交集像素（精确模式）...")

        # 获取像素数据
        pixels_a = list(self.image_a.getdata())
        pixels_b = list(self.image_b.getdata())

        # 处理交集
        result_pixels = []
        intersection_count = 0

        for i in range(len(pixels_a)):
            pixel_a = pixels_a[i]
            pixel_b = pixels_b[i]

            # 如果两个位置都有像素（alpha > 0），则保留B中的像素
            if pixel_a[3] > 0 and pixel_b[3] > 0:
                # 交集位置：保留B图层像素
                result_pixels.append(pixel_b)
                intersection_count += 1
            else:
                # 非交集位置：设为透明
                result_pixels.append((0, 0, 0, 0))

        # 生成结果图像
        self.result_image = Image.new('RGBA', self.image_b.size)
        self.result_image.putdata(result_pixels)

        print(f"  ✓ 保留了 {intersection_count:,} 个交集像素")
        return True

    def save_result(self):
        """保存处理结果"""
        print(f"\n💾 保存结果...")

        try:
            # 确保输出目录存在
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图像 - 使用UTF-8安全的路径
            output_path_safe = str(self.output_path).encode('utf-8').decode('utf-8')
            self.result_image.save(output_path_safe, 'PNG', optimize=True)

            # 验证文件
            if self.output_path.exists():
                file_size = self.output_path.stat().st_size
                print(f"  ✓ 已保存到: {self.output_path}")
                print(f"  ✓ 文件大小: {file_size:,} bytes")
                return True
            else:
                raise Exception("文件保存失败")

        except Exception as e:
            print(f"  ❌ 保存失败: {e}")
            return False

    def process(self, use_optimized=True):
        """执行完整的交集保留流程"""
        try:
            print("=" * 60)
            print("✂️ PNG图层交集保留工具")
            print("=" * 60)

            # 1. 验证输入
            if not self.validate_inputs():
                return False

            # 2. 分析交集
            intersection_count = self.calculate_intersection_stats()

            # 3. 保留交集
            if use_optimized:
                if not self.keep_intersection_optimized():
                    return False
            else:
                if not self.keep_intersection_precise():
                    return False

            # 4. 保存结果
            if not self.save_result():
                return False

            print("\n" + "=" * 60)
            print("✅ 交集保留完成!")
            print(f"📁 输入A: {self.png_a_path.name}")
            print(f"📁 输入B: {self.png_b_path.name}")
            print(f"📁 输出: {self.output_path.name}")
            print(f"📐 尺寸: {self.image_a.size[0]}×{self.image_a.size[1]} px")
            if intersection_count > 0:
                print(f"✂️ 保留: {intersection_count:,} 个交集像素")
            else:
                print("ℹ️ 无交集像素，输出为透明图像")
            print("=" * 60)

            return True

        except Exception as e:
            # 确保错误信息的UTF-8编码安全
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"❌ 处理失败: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("PNG图层交集保留工具")
        print()
        print("用法:")
        print("  python png_intersection_keeper.py <图像A> <图像B> [输出文件]")
        print()
        print("功能:")
        print("  计算图像A和B的像素交集，然后仅保留B中与A交集的部分")
        print()
        print("示例:")
        print("  python png_intersection_keeper.py layer1.png layer2.png result.png")
        print("  python png_intersection_keeper.py layer1.png layer2.png")
        print()
        print("注意:")
        print("  - 两个输入图像必须具有相同的尺寸")
        print("  - 输入图像会自动转换为RGBA格式")
        print("  - 如果不指定输出文件，会自动生成文件名")
        print("  - 非交集部分将变为完全透明")
        return 1

    try:
        # 使用UTF-8安全的命令行参数处理
        png_a_path = sys.argv[1].encode('utf-8').decode('utf-8') if isinstance(sys.argv[1], str) else str(sys.argv[1])
        png_b_path = sys.argv[2].encode('utf-8').decode('utf-8') if isinstance(sys.argv[2], str) else str(sys.argv[2])
        output_path = None
        if len(sys.argv) > 3:
            output_path = sys.argv[3].encode('utf-8').decode('utf-8') if isinstance(sys.argv[3], str) else str(sys.argv[3])

        # 检查输入文件路径
        if not Path(png_a_path).exists():
            print(f"❌ 图像A不存在: {png_a_path}")
            return 1

        if not Path(png_b_path).exists():
            print(f"❌ 图像B不存在: {png_b_path}")
            return 1

        # 创建处理器
        keeper = PNGIntersectionKeeper(png_a_path, png_b_path, output_path)

        # 执行处理
        success = keeper.process()

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


if __name__ == "__main__":
    exit(main())