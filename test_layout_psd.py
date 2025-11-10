#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from psd_tools import PSDImage
from PIL import Image

# 加载白色填充的布局PSD
psd_path = "backend/storage/layout_templates/e28fbd7f-46ef-4d34-83f5-5c06e2276661_layout.psd"
psd = PSDImage.open(psd_path)

print(f"画布尺寸: {psd.width} × {psd.height}")
print(f"总图层数: {len(list(psd.descendants()))}")

# 检查前2个图层
for i, layer in enumerate(psd.descendants()):
    if layer.is_group():
        continue
    if i >= 2:
        break

    print(f"\n图层 {i}: {layer.name}")
    print(f"  BBox: {layer.bbox}")

    # 获取图层图像
    try:
        layer_img = layer.topil()
        print(f"  图层图像尺寸: {layer_img.size}")
        print(f"  图层图像模式: {layer_img.mode}")

        # 检查像素
        if layer_img.mode == 'RGBA':
            r, g, b, a = layer_img.split()

            # 保存alpha通道看看
            alpha_path = f"test_layer_{i}_alpha.png"
            a.save(alpha_path)
            print(f"  Alpha通道已保存: {alpha_path}")

            # 检查是否全白
            pixels = layer_img.load()
            sample_pixel = pixels[0, 0]
            print(f"  左上角像素 (0,0): {sample_pixel}")

            if layer_img.width > 10 and layer_img.height > 10:
                center_pixel = pixels[layer_img.width//2, layer_img.height//2]
                print(f"  中心像素: {center_pixel}")
    except Exception as e:
        print(f"  ❌ 无法读取图层: {e}")
