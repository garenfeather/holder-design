#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

"""
精确像素描边工具

功能：对PNG图案进行精确的像素级描边
特点：
- 精确控制：每个像素都精确控制，无模糊效应
- 基于形态学：使用形态学膨胀操作，避免距离变换的连续值问题
- 外侧描边：只在图案外部添加描边，不覆盖原始内容
- 像素完美：输入N像素，输出就是精确的N像素描边

算法：
1. 提取PNG的alpha通道并转换为二值掩码
2. 使用形态学膨胀操作精确扩展指定像素数
3. 减去原始图案区域，得到纯外侧描边
4. 应用描边颜色并与原图合成
"""

from PIL import Image, ImageFilter, ImageChops
from pathlib import Path
import argparse
import time


class PrecisePixelStroker:
    """精确像素描边器"""

    def __init__(self, input_path, output_path=None, stroke_width=2, stroke_color=(255, 255, 255, 255)):
        """
        初始化精确像素描边器

        Args:
            input_path: 输入PNG文件路径
            output_path: 输出文件路径，如果为None则自动生成
            stroke_width: 描边宽度（像素）- 精确控制
            stroke_color: 描边颜色 (R, G, B, A)
        """
        self.input_path = Path(input_path)
        self.stroke_width = stroke_width
        self.stroke_color = stroke_color
        self.output_path = Path(output_path) if output_path else self._generate_output_path()

    def _generate_output_path(self):
        """生成输出文件路径"""
        stem = self.input_path.stem
        suffix = self.input_path.suffix
        return self.input_path.parent / f"{stem}_precise_stroke_{self.stroke_width}px{suffix}"

    def validate_input(self):
        """验证输入文件"""
        print(f"📂 验证输入文件...")

        if not self.input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {self.input_path}")

        print(f"  ✓ 输入文件: {self.input_path.name}")

        # 加载并验证图像
        try:
            self.image = Image.open(self.input_path).convert('RGBA')
            print(f"  ✓ 图像尺寸: {self.image.size[0]}×{self.image.size[1]} px")
        except Exception as e:
            raise ValueError(f"无法加载图像文件: {e}")

        # 检查是否有有效像素
        alpha = self.image.split()[3]
        valid_pixels = sum(1 for pixel in alpha.getdata() if pixel > 0)
        total_pixels = self.image.size[0] * self.image.size[1]

        if valid_pixels == 0:
            raise ValueError("图像中没有可见像素（完全透明）")

        print(f"  ✓ 有效像素: {valid_pixels:,} / {total_pixels:,} ({valid_pixels/total_pixels*100:.1f}%)")
        return True

    def create_precise_stroke_mask(self):
        """创建精确的描边蒙版 - 基于形态学操作"""
        print(f"\n🎯 创建精确描边蒙版 (宽度: {self.stroke_width} 像素)...")

        # 提取alpha通道并转换为严格的二值掩码
        alpha = self.image.split()[3]

        # 创建二值掩码：>0的像素设为255，其他为0
        binary_mask = alpha.point(lambda x: 255 if x > 0 else 0)
        original_pixels = sum(1 for pixel in binary_mask.getdata() if pixel > 0)
        print(f"  ✓ 原始图案像素: {original_pixels:,}")

        # 使用形态学膨胀进行精确扩展
        # 每次膨胀恰好扩展1像素
        stroke_mask = binary_mask.copy()

        for i in range(self.stroke_width):
            # 使用3x3的MaxFilter进行1像素精确膨胀
            # MaxFilter会将每个像素替换为其3x3邻域内的最大值
            stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(3))

            # 统计当前膨胀后的像素数
            current_pixels = sum(1 for pixel in stroke_mask.getdata() if pixel > 0)
            print(f"  · 膨胀第{i+1}层: {current_pixels:,} 像素")

        # 从膨胀后的蒙版中减去原始蒙版，得到纯描边区域
        pure_stroke_mask = ImageChops.subtract(stroke_mask, binary_mask)

        # 统计纯描边像素
        stroke_pixels = sum(1 for pixel in pure_stroke_mask.getdata() if pixel > 0)
        print(f"  ✓ 纯描边像素: {stroke_pixels:,}")

        # 验证精确性：总像素应该等于原始+描边
        total_pixels = sum(1 for pixel in stroke_mask.getdata() if pixel > 0)
        expected_total = original_pixels + stroke_pixels

        if total_pixels == expected_total:
            print(f"  ✓ 像素计算精确: {original_pixels:,} + {stroke_pixels:,} = {total_pixels:,}")
        else:
            print(f"  ⚠️ 像素计算偏差: 期望{expected_total:,}, 实际{total_pixels:,}")

        self.stroke_mask = pure_stroke_mask
        return True

    def apply_stroke_color_precise(self):
        """应用描边颜色 - 精确合成"""
        print(f"\n🎨 应用描边颜色...")

        # 创建描边图层
        stroke_layer = Image.new('RGBA', self.image.size, self.stroke_color)

        # 创建结果画布
        self.result = Image.new('RGBA', self.image.size, (0, 0, 0, 0))

        # 首先放置描边（底层）- 使用精确的二值蒙版
        self.result.paste(stroke_layer, (0, 0), self.stroke_mask)

        # 然后放置原图案（顶层）- 保持原始透明度
        self.result.paste(self.image, (0, 0), self.image)

        # 统计最终结果
        final_pixels = sum(1 for pixel in self.result.getdata() if pixel[3] > 0)
        original_pixels = sum(1 for pixel in self.image.getdata() if pixel[3] > 0)
        stroke_pixels = sum(1 for pixel in self.stroke_mask.getdata() if pixel > 0)

        print(f"  ✓ 原始像素: {original_pixels:,}")
        print(f"  ✓ 描边像素: {stroke_pixels:,}")
        print(f"  ✓ 最终像素: {final_pixels:,}")
        print(f"  ✓ 描边宽度: {self.stroke_width} 像素 (精确)")

        return True

    def save_result(self):
        """保存处理结果"""
        print(f"\n💾 保存结果...")

        try:
            # 确保输出目录存在
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图像
            self.result.save(self.output_path, 'PNG', optimize=True)

            # 验证文件
            if self.output_path.exists():
                file_size = self.output_path.stat().st_size
                print(f"  ✓ 已保存到: {self.output_path}")
                print(f"  ✓ 文件大小: {file_size:,} bytes")
                return True
            else:
                raise Exception("文件保存失败")

        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"  ❌ 保存失败: {error_msg}")
            return False

    def process(self):
        """执行完整的精确描边流程"""
        try:
            print("=" * 60)
            print("🎯 精确像素描边工具")
            print("=" * 60)

            start_time = time.time()

            # 1. 验证输入
            if not self.validate_input():
                return False

            # 2. 创建精确描边蒙版
            if not self.create_precise_stroke_mask():
                return False

            # 3. 应用颜色
            if not self.apply_stroke_color_precise():
                return False

            # 4. 保存结果
            if not self.save_result():
                return False

            processing_time = time.time() - start_time

            print("\n" + "=" * 60)
            print("✅ 精确描边完成!")
            print(f"📁 输入文件: {self.input_path.name}")
            print(f"📁 输出文件: {self.output_path.name}")
            print(f"📐 图像尺寸: {self.image.size[0]}×{self.image.size[1]} px")
            print(f"🎯 描边宽度: {self.stroke_width} 像素 (精确控制)")
            print(f"🎨 描边颜色: RGBA{self.stroke_color}")
            print(f"⏱️ 处理时间: {processing_time:.2f} 秒")
            print(f"🔬 算法类型: 基于形态学的精确像素描边")
            print("=" * 60)

            return True

        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"❌ 处理失败: {error_msg}")
            import traceback
            traceback.print_exc()
            return False



def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='精确像素描边工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s logo.png 3
  %(prog)s icon.png 5
        """
    )

    parser.add_argument('input', help='输入PNG文件路径')
    parser.add_argument('stroke_width', type=int, help='描边宽度（像素）')

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    try:
        args = parser.parse_args()

        # 检查输入文件
        if not Path(args.input).exists():
            print(f"❌ 输入文件不存在: {args.input}")
            return 1

        # 验证参数
        if args.stroke_width <= 0:
            print("❌ 描边宽度必须大于0")
            return 1

        # 创建描边器 - 使用默认白色描边和自动输出路径
        stroker = PrecisePixelStroker(
            input_path=args.input,
            output_path=None,  # 自动生成
            stroke_width=args.stroke_width,
            stroke_color=(255, 255, 255, 255)  # 固定白色
        )

        # 执行描边
        success = stroker.process()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        return 1
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"❌ 程序执行失败: {error_msg}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())