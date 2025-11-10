#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 PSD 中替换指定图层的像素内容，保留全部图层结构并输出新的 PSD。
适配 pytoshop.user.nested_layers.Image(channels=...) 版本。
"""

import os, sys
from psd_tools import PSDImage
from PIL import Image
from pytoshop import enums
from pytoshop.user import nested_layers as nl

# 混合模式映射
BLEND_MAP = {
    "normal": enums.BlendMode.normal,
    "multiply": enums.BlendMode.multiply,
    "screen": enums.BlendMode.screen,
    "overlay": enums.BlendMode.overlay,
    "soft_light": enums.BlendMode.soft_light,
    "hard_light": enums.BlendMode.hard_light,
    "darken": enums.BlendMode.darken,
    "lighten": enums.BlendMode.lighten,
}

def ensure_bbox(bbox):
    """兼容 tuple / BBox 对象"""
    if bbox is None:
        return None
    if isinstance(bbox, tuple):
        x1, y1, x2, y2 = bbox
        class B: pass
        b = B()
        b.x1, b.y1, b.x2, b.y2 = x1, y1, x2, y2
        b.width, b.height = x2 - x1, y2 - y1
        return b
    return bbox

def pil_to_channels(im: Image.Image):
    """把 RGBA 转成 pytoshop 需要的 channels 列表"""
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    r, g, b, a = [c.tobytes() for c in im.split()]
    return [
        (0, r),   # Red
        (1, g),   # Green
        (2, b),   # Blue
        (-1, a),  # Alpha
    ]

def opacity_to_255(op):
    if isinstance(op, float):
        return int(round(op * 255))
    return int(op or 255)

def build_layer(node, target_name, repl_img):
    """递归构造层结构"""
    if node.is_group():
        children = [build_layer(ch, target_name, repl_img) for ch in node]
        children = [c for c in children if c is not None]
        return nl.Group(name=node.name or "", layers=children, visible=node.is_visible())

    bbox = ensure_bbox(node.bbox)
    if bbox is None or bbox.width <= 0 or bbox.height <= 0:
        return None

    w, h = bbox.width, bbox.height
    blend = BLEND_MAP.get(getattr(node, "blend_mode", "normal"), enums.BlendMode.normal)
    opacity = opacity_to_255(getattr(node, "opacity", 1.0))

    # 获取原图像
    orig = node.composite()
    if orig:
        orig = orig.convert("RGBA")
    else:
        orig = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if node.name == target_name:
        print(f"[INFO] 替换图层 {node.name} @ ({bbox.x1},{bbox.y1}) {w}x{h}")
        repl_resized = repl_img.resize((w, h), Image.LANCZOS).convert("RGBA")
        final_img = repl_resized
    else:
        final_img = orig

    channels = pil_to_channels(final_img)
    return nl.Image(
        name=node.name or "",
        visible=node.is_visible(),
        opacity=opacity,
        blend_mode=blend,
        top=bbox.y1,
        left=bbox.x1,
        bottom=bbox.y2,
        right=bbox.x2,
        channels=channels,
        color_mode=enums.ColorMode.rgb,
    )

def replace_layer(psd_path, layer_name, new_image_path, out_path):
    psd = PSDImage.open(psd_path)
    new_img = Image.open(new_image_path).convert("RGBA")
    W, H = psd.size

    layers = []
    for node in psd:
        res = build_layer(node, layer_name, new_img)
        if res:
            layers.append(res)

    doc = nl.from_layers(layers, size=(W, H), color_mode="RGB")
    with open(out_path, "wb") as f:
        doc.write(f)

    print(f"[DONE] 已输出 PSD：{out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python replace_layer_psd.py input.psd layer_name new.png [output.psd]")
        sys.exit(1)

    inp, lname, newimg = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.splitext(inp)[0] + "_replaced.psd"
    replace_layer(inp, lname, newimg, out)