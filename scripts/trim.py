#!/usr/bin/env python3
import argparse
import os
from psd_tools import PSDImage
from PIL import Image

def get_visible_bbox(pil_image: Image.Image):
    """计算非透明像素区域的边界 (left, top, right, bottom)。"""
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    alpha = pil_image.split()[-1]
    return alpha.getbbox()

def trim_layer(layer):
    """返回裁剪后的图像和偏移坐标。"""
    pil = layer.topil()
    bbox = get_visible_bbox(pil)
    if bbox is None:
        return None, (layer.left, layer.top)
    cropped = pil.crop(bbox)
    offset_x = layer.left + bbox[0]
    offset_y = layer.top + bbox[1]
    return cropped, (offset_x, offset_y)

def process_layer(layer, base_size):
    """裁剪单个图层"""
    trimmed, (x, y) = trim_layer(layer)
    if trimmed is None:
        return None
    return {"name": layer.name, "image": trimmed, "offset": (x, y), "visible": layer.is_visible()}

def process_psd(input_path, output_path):
    psd = PSDImage.open(input_path)
    base_size = psd.size
    print(f"📐 画布尺寸: {base_size[0]}x{base_size[1]}")

    from psd_tools.api.psd_image import PSDImage as PSDExport
    from psd_tools.psd.image_resources import ImageResources

    new_layers = []

    def handle_layer(l):
        if l.is_group():
            # 递归处理组
            children = []
            for sub in l:
                child = handle_layer(sub)
                if child:
                    children.append(child)
            if children:
                l._info["layers"] = children
                new_layers.append(l)
        else:
            result = process_layer(l, base_size)
            if result:
                new_layers.append(result)
        return l

    for layer in psd:
        handle_layer(layer)

    # 构建新的 PSD
    new_psd = PSDExport(
        size=base_size,
        image_resources=ImageResources(),
    )

    # 用 alpha 合成导出，因为 psd-tools 目前没有 LayerBuilder API
    from psd_tools.api.composite_image import composite_image

    result = Image.new("RGBA", base_size, (0, 0, 0, 0))
    for item in new_layers:
        if isinstance(item, dict):
            img = item["image"]
            if img and item["visible"]:
                result.alpha_composite(img, item["offset"])

    new_psd.composite_image = lambda *a, **kw: result
    new_psd.save(output_path)
    print(f"✅ 已保存修剪版 PSD：{output_path}")

def main():
    parser = argparse.ArgumentParser(description="修剪 PSD 每个图层到自身可见像素边界，保持画布尺寸。")
    parser.add_argument("input", help="输入 PSD 文件路径")
    parser.add_argument("-o", "--output", help="输出 PSD 文件路径（默认 *_trimmed.psd）")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件：{input_path}")

    output_path = args.output or os.path.splitext(input_path)[0] + "_trimmed.psd"
    process_psd(input_path, output_path)

if __name__ == "__main__":
    main()