"""
PSD 布局模板解析器 - 重写版本
功能：解析 PSD 文件，提取图层信息并匹配刀模元素
"""

import os
import io
import base64
from typing import Dict, List, Tuple
from psd_tools import PSDImage
from psd_tools.constants import Resource
from PIL import Image, ImageDraw, ImageFont


# 容差范围（mm）
TOLERANCE_MM = 0.5


def get_psd_resolution(psd: PSDImage) -> Tuple[float, float]:
    """
    获取 PSD 文件的分辨率（DPI）

    Args:
        psd: PSDImage 对象

    Returns:
        (dpi_x, dpi_y) 元组，默认 (72.0, 72.0)
    """
    try:
        res_info = psd.image_resources.get_data(Resource.RESOLUTION_INFO)
        if res_info and hasattr(res_info, 'horizontal') and hasattr(res_info, 'vertical'):
            # PSD 中的 DPI 是 Fixed 定点数格式：需要除以 65536
            dpi_x = float(res_info.horizontal) / 65536.0
            dpi_y = float(res_info.vertical) / 65536.0
            return (dpi_x, dpi_y)
    except Exception as e:
        print(f"[警告] 无法读取 PSD 分辨率: {e}")

    return (72.0, 72.0)


def px_to_mm(px: float, dpi: float) -> float:
    """
    像素转毫米

    公式: px / dpi * 25.4

    Args:
        px: 像素值
        dpi: DPI 值

    Returns:
        毫米值
    """
    return (px / dpi) * 25.4


def cm_to_mm(cm: float) -> float:
    """
    厘米转毫米

    Args:
        cm: 厘米值

    Returns:
        毫米值
    """
    return cm * 10.0


def is_size_match(size1: float, size2: float, tolerance: float = TOLERANCE_MM) -> bool:
    """
    判断两个尺寸是否匹配（考虑容差）

    Args:
        size1: 尺寸1（mm）
        size2: 尺寸2（mm）
        tolerance: 容差（mm）

    Returns:
        是否匹配
    """
    return abs(size1 - size2) <= tolerance


def parse_psd_file(psd_path: str) -> Dict:
    """
    解析 PSD 文件，提取画布和图层信息

    Args:
        psd_path: PSD 文件路径

    Returns:
        {
            'canvas_size': {'width': float, 'height': float},  # mm
            'dpi': (float, float),
            'layers': [
                {
                    'index': int,
                    'name': str,
                    'bounds': {'x': float, 'y': float, 'width': float, 'height': float}  # mm
                }
            ]
        }
    """
    # 强制输出到文件和控制台
    import sys
    def debug_print(msg):
        print(msg, flush=True)
        with open('/tmp/psd_parser_debug.log', 'a') as f:
            f.write(msg + '\n')

    debug_print(f"\n========== PSD 解析开始 ==========")
    debug_print(f"文件: {psd_path}")

    # 复制文件用于调试
    import shutil
    debug_psd_path = '/tmp/debug_uploaded.psd'
    shutil.copy2(psd_path, debug_psd_path)
    debug_print(f"已复制到: {debug_psd_path}")

    try:
        # 打开 PSD 文件
        psd = PSDImage.open(psd_path)
        debug_print(f"✓ PSD 文件打开成功")
        debug_print(f"  PSD对象: {psd}")
        debug_print(f"  PSD.width: {psd.width}")
        debug_print(f"  PSD.height: {psd.height}")

        # 测试遍历图层
        debug_print(f"\n测试遍历所有图层:")
        for i, layer in enumerate(psd.descendants()):
            debug_print(f"  [{i}] 名称='{layer.name}', is_group={layer.is_group()}, bbox={layer.bbox if hasattr(layer, 'bbox') else 'N/A'}")

        # 获取分辨率
        dpi_x, dpi_y = get_psd_resolution(psd)
        debug_print(f"✓ DPI: {dpi_x} x {dpi_y}")

        # 获取画布尺寸
        canvas_w_px = psd.width
        canvas_h_px = psd.height
        canvas_w_mm = px_to_mm(canvas_w_px, dpi_x)
        canvas_h_mm = px_to_mm(canvas_h_px, dpi_y)
        debug_print(f"✓ 画布: {canvas_w_px}x{canvas_h_px}px = {canvas_w_mm:.2f}x{canvas_h_mm:.2f}mm")

        # 提取所有图层
        layers = []
        layer_count = 0

        debug_print(f"\n---------- 提取图层 ----------")
        descendants = list(psd.descendants())
        debug_print(f"  descendants 数量: {len(descendants)}")

        for layer in descendants:
            if layer.is_group():
                continue  # 跳过组

            layer_count += 1

            # 尝试多种方式获取图层尺寸
            bbox = None
            width_px = 0
            height_px = 0
            left = 0
            top = 0

            # 方法1: 使用 bbox（可见内容边界）
            if hasattr(layer, 'bbox') and layer.bbox:
                bbox = layer.bbox
                if bbox and len(bbox) == 4:
                    left, top, right, bottom = bbox
                    width_px = right - left
                    height_px = bottom - top

            # 方法2: 如果 bbox 无效，尝试使用 width/height 属性
            if width_px <= 0 or height_px <= 0:
                if hasattr(layer, 'width') and hasattr(layer, 'height'):
                    width_px = layer.width
                    height_px = layer.height
                    if hasattr(layer, 'left') and hasattr(layer, 'top'):
                        left = layer.left
                        top = layer.top

            # 方法3: 使用 offset 和 size
            if width_px <= 0 or height_px <= 0:
                if hasattr(layer, 'offset') and hasattr(layer, 'size'):
                    left, top = layer.offset
                    width_px, height_px = layer.size

            debug_print(f"  [{layer_count}] '{layer.name}' - bbox={bbox}, size={width_px}x{height_px}px")

            if width_px <= 0 or height_px <= 0:
                debug_print(f"    -> 跳过（尺寸无效）")
                continue

            # 转换为毫米
            x_mm = px_to_mm(left, dpi_x)
            y_mm = px_to_mm(top, dpi_y)
            width_mm = px_to_mm(width_px, dpi_x)
            height_mm = px_to_mm(height_px, dpi_y)

            layer_info = {
                'index': len(layers),
                'name': layer.name,
                'bounds': {
                    'x': round(x_mm, 2),
                    'y': round(y_mm, 2),
                    'width': round(width_mm, 2),
                    'height': round(height_mm, 2)
                }
            }

            layers.append(layer_info)
            debug_print(f"  [{len(layers)}] '{layer.name}' - {width_px}x{height_px}px = {width_mm:.2f}x{height_mm:.2f}mm")

        debug_print(f"\n✓ 共提取 {len(layers)} 个有效图层")
        debug_print(f"========== PSD 解析完成 ==========\n")

        return {
            'canvas_size': {
                'width': round(canvas_w_mm, 2),
                'height': round(canvas_h_mm, 2)
            },
            'dpi': (dpi_x, dpi_y),
            'layers': layers
        }

    except Exception as e:
        print(f"\n✗ PSD 解析失败: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"PSD 文件解析失败: {str(e)}")


def match_layers_to_die_elements(layers: List[Dict], die_elements: List[Dict]) -> Dict:
    """
    匹配图层与刀模元素（基于裁切尺寸）

    注意：
    - a×b 和 b×a 被视为相同元素（考虑旋转）
    - 每个图层只匹配一次
    - 使用容差进行尺寸比较

    Args:
        layers: 图层列表
        die_elements: 刀模元素列表

    Returns:
        {
            'success': bool,
            'matched': [...],
            'unmatched_layers': [...]
        }
    """
    print(f"\n========== 开始匹配 ==========")
    print(f"图层数量: {len(layers)}")
    print(f"刀模元素数量: {len(die_elements)}")

    matched = []
    unmatched_layers = []
    # 移除 used_elements - 允许同一元素被多个图层使用

    for layer in layers:
        layer_w_mm = layer['bounds']['width']
        layer_h_mm = layer['bounds']['height']
        layer_name = layer.get('name', f"图层 {layer['index']}")

        found = False

        # 遍历所有刀模元素
        for element in die_elements:
            # 允许同一元素被多次使用（不再检查 used_elements）

            # 刀模元素尺寸：cm -> mm
            elem_w_cm = element['cutSize']['width']
            elem_h_cm = element['cutSize']['height']
            elem_w_mm = cm_to_mm(elem_w_cm)
            elem_h_mm = cm_to_mm(elem_h_cm)

            # 判断是否匹配（考虑旋转）
            rotation = None

            # 无旋转匹配
            if is_size_match(layer_w_mm, elem_w_mm) and is_size_match(layer_h_mm, elem_h_mm):
                rotation = 0
            # 旋转 90 度匹配
            elif is_size_match(layer_w_mm, elem_h_mm) and is_size_match(layer_h_mm, elem_w_mm):
                rotation = 90

            if rotation is not None:
                # 匹配成功
                matched.append({
                    'layer_index': layer['index'],
                    'layer_name': layer_name,
                    'element_id': element['id'],
                    'element_name': element['name'],
                    'rotation': rotation,
                    'position': {
                        'x': layer['bounds']['x'],
                        'y': layer['bounds']['y']
                    },
                    'cut_size': element['cutSize']
                })
                # 移除 used_elements.add - 允许重复匹配
                found = True

                print(f"  ✓ '{layer_name}' ({layer_w_mm:.2f}x{layer_h_mm:.2f}mm) -> '{element['name']}' ({elem_w_mm:.2f}x{elem_h_mm:.2f}mm, 旋转{rotation}°)")
                break

        if not found:
            # 未匹配
            unmatched_layers.append({
                'index': layer['index'],
                'name': layer_name,
                'size': {
                    'width': round(layer_w_mm, 2),
                    'height': round(layer_h_mm, 2)
                }
            })
            print(f"  ✗ '{layer_name}' ({layer_w_mm:.2f}x{layer_h_mm:.2f}mm) - 未找到匹配的刀模元素")

    success = len(unmatched_layers) == 0

    print(f"\n匹配结果: {len(matched)} 个成功, {len(unmatched_layers)} 个失败")
    print(f"========== 匹配完成 ==========\n")

    return {
        'success': success,
        'matched': matched,
        'unmatched_layers': unmatched_layers
    }


def generate_preview_image(canvas_size: Dict, elements: List[Dict]) -> str:
    """
    生成白色画布预览图，显示元素边框和名称

    Args:
        canvas_size: {'width': mm, 'height': mm}
        elements: 布局元素列表

    Returns:
        Base64 编码的图片字符串 "data:image/png;base64,..."
    """
    # 缩放比例：1mm = 2px
    SCALE = 2
    width_px = int(canvas_size['width'] * SCALE)
    height_px = int(canvas_size['height'] * SCALE)

    # 创建白色画布
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    # 加载字体
    try:
        font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 14)
    except:
        try:
            font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
        except:
            font = ImageFont.load_default()

    # 绘制每个元素
    for element in elements:
        x = element['position']['x'] * SCALE
        y = element['position']['y'] * SCALE

        # 支持两种命名方式：驼峰(cutSize)和下划线(cut_size)
        cut_size = element.get('cutSize') or element.get('cut_size')
        element_name = element.get('elementName') or element.get('element_name')

        w = cm_to_mm(cut_size['width']) * SCALE
        h = cm_to_mm(cut_size['height']) * SCALE

        # 考虑旋转
        if element['rotation'] == 90:
            w, h = h, w

        # 绘制矩形边框
        draw.rectangle(
            [x, y, x + w, y + h],
            outline='black',
            width=2
        )

        # 绘制元素名称（居中）
        text = element_name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = x + (w - text_w) / 2
        text_y = y + (h - text_h) / 2
        draw.text((text_x, text_y), text, fill='black', font=font)

    # 转换为 Base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_data}"


if __name__ == '__main__':
    print("PSD 布局解析器 - 重写版本")
