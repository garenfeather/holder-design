#!/usr/bin/env python3
"""
PSD view/parts slicer

功能:
1) 检查输入 PSD 是否包含名为: view, part1, part2, part3, part4 的图层(可嵌套)。若缺失则退出。
2) 以 view 图层为选区/画布，分别裁切出 part1-4 到独立 PNG 文件：
   - 输出 PNG 画布尺寸 == view 图层的尺寸
   - PNG 内部保持原始图层的相对位置与形状
   - 使用 view 图层的透明度作为裁切选区（对 partX 进行相交裁切）
3) 提取 view 图层为 PNG（尺寸同 view）
4) 将上述等尺寸的 view、part1-4 PNG 重新分层写入一个同尺寸的 PSD，输出到当前目录

依赖:
- psd-tools>=1.9
- Pillow
- 可选: pytoshop (用于写分层 PSD；若未安装则跳过 PSD 导出，仅输出 PNG)

用法:
  python3 scripts/psd_crop_view_parts.py input.psd

说明:
- 不考虑蒙版样式、混合模式、组透明度等复杂结构；使用 layer.composite() 的像素结果。
- 若你项目内已有可写 PSD 的工具(如 full_scale.py)，可在 build_layered_psd() 处替换为该逻辑。
"""

import argparse
import os
import sys
from typing import Dict, Optional

from PIL import Image, ImageChops

try:
    # psd-tools >=1.9 推荐从顶层导入 PSDImage
    from psd_tools import PSDImage
except Exception:
    # 兼容旧版本（不再推荐）
    try:
        from psd_tools.api.psd_image import PSDImage  # type: ignore
    except Exception as e:
        print(e, file=sys.stderr)
        raise


REQUIRED_LAYER_NAMES = ["view", "part1", "part2", "part3", "part4"]


def find_layer_by_name(psd: PSDImage, name: str):
    for layer in psd.descendants():
        # 跳过组，仅找像素层
        try:
            if getattr(layer, 'name', None) == name and not layer.is_group():
                return layer
        except Exception:
            # 某些节点可能没有 is_group 属性
            if getattr(layer, 'name', None) == name:
                return layer
    return None


def load_required_layers(psd: PSDImage) -> Dict[str, object]:
    layers = {}
    for name in REQUIRED_LAYER_NAMES:
        layer = find_layer_by_name(psd, name)
        if not layer:
            return {}
        layers[name] = layer
    return layers


def layer_to_image_and_bbox(layer) -> (Image.Image, tuple):
    """返回该图层渲染后的 RGBA 图与 bbox(left, top, right, bottom)。"""
    img = layer.composite()
    # psd-tools bbox: (x1, y1, x2, y2) 或 BBox 对象
    bbox = layer.bbox
    # 标准化为元组
    try:
        # 新版可能是 BBox 对象
        left, top, right, bottom = bbox.x1, bbox.y1, bbox.x2, bbox.y2
    except AttributeError:
        # 旧版为 tuple
        left, top, right, bottom = bbox
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return img, (left, top, right, bottom)


def crop_part_with_view_mask(part_img: Image.Image, part_bbox: tuple, view_bbox: tuple, view_alpha: Image.Image) -> Image.Image:
    """返回尺寸与 view 相同的透明画布，将 part_img 放置在相对位置，并用 view 的 alpha 相交裁切。"""
    v_left, v_top, v_right, v_bottom = view_bbox
    v_w, v_h = v_right - v_left, v_bottom - v_top

    p_left, p_top, p_right, p_bottom = part_bbox
    dx, dy = p_left - v_left, p_top - v_top

    # 目标画布（透明）
    out = Image.new('RGBA', (v_w, v_h), (0, 0, 0, 0))

    # 计算与 view 交叠区域
    # part 放到 (dx, dy) 范围内
    part_alpha = part_img.split()[3]

    # 对应的 view 区域
    mask_region = view_alpha.crop((dx, dy, dx + part_img.width, dy + part_img.height))
    # 相交: min(part_alpha, view_alpha_region)
    intersect_mask = ImageChops.lighter(ImageChops.invert(ImageChops.lighter(ImageChops.invert(part_alpha), ImageChops.invert(mask_region))), Image.new('L', part_alpha.size, 0))
    # 上面等价于取较小值；可直接用 multiply 近似
    intersect_mask = ImageChops.multiply(part_alpha, mask_region)

    out.paste(part_img, (dx, dy), mask=intersect_mask)
    return out


def save_png(img: Image.Image, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format='PNG')


def build_layered_psd(output_psd_path: str, canvas_size: tuple, layer_images: Dict[str, Image.Image]) -> Optional[str]:
    """尝试用 pytoshop 写分层 PSD；若不可用则返回 None。

    兼容 pytoshop 1.2.x（无 frompil/psd 模块），使用 nested_layers_to_psd 接口。
    """
    try:
        from pytoshop.user import nested_layers as nl
        import numpy as np
    except Exception:
        # 未安装 pytoshop 或 numpy，跳过 PSD 写入
        return None

    width, height = canvas_size
    layers = []
    # 注意：pytoshop 在写入时会反转我们传入的顺序（以满足底层格式），
    # 因此为了让最终 PSD 的显示顺序与“目前相反”，这里传入与现在相同的顺序，
    # 使最终结果为相反顺序。
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
            -1: a_arr,  # Alpha (transparency)
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

    try:
        psdfile = nl.nested_layers_to_psd(
            layers=layers,
            color_mode=nl.enums.ColorMode.rgb,
            # 注意: pytoshop 文档标注为 (height, width)，
            # 但实际导出的画布与我们需求相反，这里按 (width, height)
            # 以匹配 PIL Image.size 的 (width, height)
            size=(width, height),
            compression=nl.enums.Compression.raw,
        )
        with open(output_psd_path, 'wb') as f:
            psdfile.write(f)
        return output_psd_path
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Slice PSD by view selection and export part1-4 as PNG and layered PSD.')
    parser.add_argument('input_psd', help='输入 PSD 文件路径')
    parser.add_argument('--keep-png', action='store_true', help='生成PSD后保留中间PNG文件（默认会在成功生成PSD后清理）')
    args = parser.parse_args()

    in_path = args.input_psd
    out_dir = '.'

    if not os.path.isfile(in_path):
        print(f"找不到输入文件: {in_path}", file=sys.stderr)
        sys.exit(1)

    psd = PSDImage.open(in_path)

    layers = load_required_layers(psd)
    if not layers:
        print(f"PSD 缺少必要图层: {', '.join(REQUIRED_LAYER_NAMES)}", file=sys.stderr)
        sys.exit(2)

    view_layer = layers['view']
    # 统一前缀用于中间PNG文件命名
    stem = os.path.splitext(os.path.basename(in_path))[0]
    view_img, view_bbox = layer_to_image_and_bbox(view_layer)
    v_left, v_top, v_right, v_bottom = view_bbox
    v_w, v_h = v_right - v_left, v_bottom - v_top
    view_alpha = view_img.split()[3]

    # 输出 view.png
    view_png_path = os.path.join(out_dir, f'{stem}_view.png')
    save_png(view_img, view_png_path)

    out_images: Dict[str, Image.Image] = {'view': view_img}

    # 处理 part1-4
    for name in ['part1', 'part2', 'part3', 'part4']:
        part_layer = layers[name]
        part_img, part_bbox = layer_to_image_and_bbox(part_layer)
        cropped = crop_part_with_view_mask(part_img, part_bbox, view_bbox, view_alpha)
        out_images[name] = cropped
        save_png(cropped, os.path.join(out_dir, f'{stem}_{name}.png'))

    # 尝试写分层 PSD（输出到当前目录，文件名为 <输入名>_cut.psd）
    psd_out_path = os.path.join('.', f"{stem}_cut.psd")
    written = build_layered_psd(psd_out_path, (v_w, v_h), out_images)
    if written:
        print(f"已输出 PSD: {os.path.abspath(written)}")
        # 若成功生成PSD，且未指定保留PNG，则清理中间PNG文件
        if not args.keep_png:
            try:
                to_remove = [view_png_path] + [os.path.join(out_dir, f'{stem}_{n}.png') for n in ['part1','part2','part3','part4']]
                removed = []
                for p in to_remove:
                    if os.path.exists(p):
                        os.remove(p)
                        removed.append(os.path.basename(p))
                if removed:
                    print(f"已清理中间文件: {', '.join(removed)}")
            except Exception as e:
                print(f"清理中间文件时出错: {e}")
    else:
        print("未安装 pytoshop，跳过 PSD 写入，仅输出 PNG。要导出 PSD，请: pip install pytoshop")
    print("完成。")


if __name__ == '__main__':
    main()
