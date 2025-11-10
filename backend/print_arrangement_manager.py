#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
排版成品管理器
功能：将用户的素材排版保存为独立的PSD和预览图
参考：psd_cropper.py 的图层处理逻辑
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from PIL import Image
from psd_tools import PSDImage

try:
    from pytoshop.user import nested_layers as nl
    import numpy as np
    PYTOSHOP_AVAILABLE = True
except Exception:
    PYTOSHOP_AVAILABLE = False

from layout_template_manager import LayoutTemplateManager
from die_manager import DieManager


class PrintArrangementManager:
    """排版成品管理器"""

    def __init__(self, storage_dir: str = "storage/print_arrangements"):
        self.storage_dir = Path(storage_dir)
        self.index_file = self.storage_dir / "arrangements.json"

        # 确保目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 初始化索引文件
        if not self.index_file.exists():
            self._save_index([])

    def _save_index(self, data: List[Dict]):
        """保存索引文件"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> List[Dict]:
        """加载索引文件"""
        if not self.index_file.exists():
            return []
        with open(self.index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_arrangement(self, template_id: str, material_mappings: Dict[str, str]) -> Optional[Dict]:
        """
        创建排版成品

        Args:
            template_id: 布局模板ID
            material_mappings: 素材映射 {layoutElementId: materialId}

        Returns:
            排版成品信息，如果失败返回None
        """
        try:
            print("\n" + "=" * 60)
            print("🎨 创建排版成品")
            print("=" * 60)

            # 1. 加载模板
            template_manager = LayoutTemplateManager()
            template = template_manager.get_template(template_id)
            if not template:
                print(f"❌ 模板不存在: {template_id}")
                return None

            # 检查是否有白色填充PSD
            if not template.get('layoutPsdFileName'):
                print(f"❌ 模板缺少布局PSD文件")
                return None

            layout_psd_path = os.path.join(template_manager.storage_dir, template['layoutPsdFileName'])
            if not os.path.exists(layout_psd_path):
                print(f"❌ 布局PSD文件不存在: {layout_psd_path}")
                return None

            print(f"📂 加载布局PSD: {layout_psd_path}")

            # 2. 加载布局PSD
            psd = PSDImage.open(str(layout_psd_path))
            canvas_width = psd.width
            canvas_height = psd.height
            print(f"📐 画布尺寸: {canvas_width} × {canvas_height} 像素")

            # 3. 处理图层并替换素材
            processed_layers = self._process_layers_with_materials(
                psd, template, material_mappings, canvas_width, canvas_height
            )

            if not processed_layers:
                print(f"⚠️  没有可用的图层（没有放置素材）")
                return None

            print(f"✓ 共处理 {len(processed_layers)} 个图层")

            # 4. 生成文件名
            arrangement_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            arrangement_name = f"排版成品_{timestamp}"
            psd_filename = f"{arrangement_id}.psd"
            preview_filename = f"{arrangement_id}.png"

            psd_path = self.storage_dir / psd_filename
            preview_path = self.storage_dir / preview_filename

            # 5. 构建PSD文件
            print(f"\n📝 生成PSD文件...")
            if not self._build_layered_psd(str(psd_path), (canvas_width, canvas_height), processed_layers):
                print(f"❌ PSD生成失败")
                return None

            print(f"✓ PSD已保存: {psd_path}")

            # 6. 生成预览图
            print(f"\n🖼️  生成预览图...")
            if not self._generate_preview_png(str(preview_path), (canvas_width, canvas_height), processed_layers):
                print(f"⚠️  预览图生成失败")
                preview_filename = None

            if preview_filename:
                print(f"✓ 预览图已保存: {preview_path}")

            # 7. 保存到索引
            arrangement = {
                "id": arrangement_id,
                "name": arrangement_name,
                "psdFileName": psd_filename,
                "previewFileName": preview_filename,
                "createdAt": datetime.now().isoformat()
            }

            index = self._load_index()
            index.append(arrangement)
            self._save_index(index)

            print(f"\n✅ 排版成品创建完成!")
            print(f"ID: {arrangement_id}")
            print("=" * 60)

            return arrangement

        except Exception as e:
            print(f"\n❌ 创建排版成品失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_layers_with_materials(self, psd: PSDImage, template: Dict,
                                      material_mappings: Dict[str, str],
                                      canvas_width: int, canvas_height: int) -> List[Dict]:
        """
        处理图层并替换素材

        正确流程：
        1. 读取布局PSD的图层（白色填充的图层）
        2. 保持图层的原始位置和尺寸
        3. 将素材图片的可见像素替换掉图层中的白色像素
        4. 生成与画布同尺寸的PNG，并保持图层相对于画布的位置一致

        Returns:
            处理后的图层列表 [{name, image}]
        """
        processed_layers = []
        die_mgr = DieManager()

        # 遍历PSD图层
        for layer in psd.descendants():
            if layer.is_group():
                continue

            # 图层名称就是元素ID（去除首尾空格和空字节）
            element_id = layer.name.strip().rstrip('\x00')

            # 查找对应的布局元素
            element = None
            for elem in template.get('elements', []):
                if elem.get('id') == element_id:
                    element = elem
                    break

            if not element:
                print(f"  跳过图层: {layer.name} (未找到对应元素)")
                continue

            # 检查该元素是否有素材
            material_id = material_mappings.get(element_id)
            if not material_id:
                print(f"  跳过图层: {layer.name} (无素材)")
                continue

            # 加载素材图片
            material_file_path = die_mgr.get_material_file_path(material_id)
            if not material_file_path or not material_file_path.exists():
                print(f"  跳过图层: {layer.name} (素材文件不存在)")
                continue

            # 获取图层位置信息
            bbox = layer.bbox
            try:
                left, top, right, bottom = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            except AttributeError:
                left, top, right, bottom = bbox

            layer_width = right - left
            layer_height = bottom - top

            # 加载素材图片
            material_img = Image.open(material_file_path)
            if material_img.mode != 'RGBA':
                material_img = material_img.convert('RGBA')

            # 获取白色填充图层，用于确定可见区域
            try:
                template_layer_img = layer.topil()
            except Exception:
                template_layer_img = None

            if template_layer_img is None:
                print(f"  跳过图层 {layer_index}: {layer.name} (无法读取模板图层像素)")
                layer_index += 1
                continue

            if template_layer_img.mode != 'RGBA':
                template_layer_img = template_layer_img.convert('RGBA')

            # 调整素材尺寸以匹配图层尺寸
            if material_img.size != (layer_width, layer_height):
                material_img = material_img.resize((layer_width, layer_height), Image.LANCZOS)

            # 关键：用白色图层的alpha通道作为遮罩，限制素材只显示在白色区域
            template_alpha = template_layer_img.split()[-1]

            # 检查是否有可见像素
            if not template_alpha.getbbox():
                print(f"  跳过图层 {layer_index}: {layer.name} (模板图层无可见像素)")
                layer_index += 1
                continue

            # 将素材的RGB通道与白色图层的alpha通道合并
            r, g, b, _ = material_img.split()
            masked_material = Image.merge('RGBA', (r, g, b, template_alpha))

            # 生成与画布同尺寸的PNG，并在对应位置粘贴素材
            canvas_layer = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
            canvas_layer.paste(masked_material, (left, top), masked_material)

            processed_layers.append({
                'name': element.get('elementName', layer.name),
                'image': canvas_layer,
                'bbox': (left, top, right, bottom)  # 保存实际可见区域
            })

            print(f"  ✓ 处理图层: {layer.name} ({element.get('elementName')}) (已替换素材，位置: {left},{top})")

        return processed_layers

    def _build_layered_psd(self, output_path: str, canvas_size: tuple, layers: List[Dict]) -> bool:
        """
        构建分层PSD文件（参考psd_cropper._build_layered_psd）

        Args:
            output_path: 输出文件路径
            canvas_size: 画布尺寸 (width, height)
            layers: 图层列表 [{name, image}]

        Returns:
            是否成功
        """
        if not PYTOSHOP_AVAILABLE:
            print("❌ pytoshop未安装，无法生成PSD")
            return False

        try:
            width, height = canvas_size
            psd_layers = []

            for layer_data in layers:
                pil_img = layer_data['image']
                bbox = layer_data.get('bbox')

                # 确保是RGBA模式
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')

                # 如果有bbox，裁剪到实际可见区域
                if bbox:
                    left, top, right, bottom = bbox
                    # 裁剪画布大小的图像到实际可见区域
                    cropped_img = pil_img.crop(bbox)

                    # 分离通道并转换为numpy数组
                    r, g, b, a = cropped_img.split()
                    r_arr = np.array(r, dtype=np.uint8)
                    g_arr = np.array(g, dtype=np.uint8)
                    b_arr = np.array(b, dtype=np.uint8)
                    a_arr = np.array(a, dtype=np.uint8)

                    # 创建pytoshop图层对象（使用实际边界）
                    lyr = nl.Image(
                        name=layer_data['name'],
                        top=top,
                        left=left,
                        bottom=bottom,
                        right=right,
                        channels={
                            0: r_arr,
                            1: g_arr,
                            2: b_arr,
                            -1: a_arr,
                        },
                        color_mode=nl.enums.ColorMode.rgb,
                        visible=True,
                        opacity=255,
                    )
                else:
                    # 没有bbox，使用整个画布（旧逻辑）
                    if pil_img.size != (width, height):
                        pil_img = pil_img.copy().resize((width, height), Image.LANCZOS)

                    r, g, b, a = pil_img.split()
                    r_arr = np.array(r, dtype=np.uint8)
                    g_arr = np.array(g, dtype=np.uint8)
                    b_arr = np.array(b, dtype=np.uint8)
                    a_arr = np.array(a, dtype=np.uint8)

                    lyr = nl.Image(
                        name=layer_data['name'],
                        top=0,
                        left=0,
                        bottom=height,
                        right=width,
                        channels={
                            0: r_arr,
                            1: g_arr,
                            2: b_arr,
                            -1: a_arr,
                        },
                        color_mode=nl.enums.ColorMode.rgb,
                        visible=True,
                        opacity=255,
                    )

                psd_layers.append(lyr)

            # 生成PSD文件
            psdfile = nl.nested_layers_to_psd(
                layers=psd_layers,
                color_mode=nl.enums.ColorMode.rgb,
                size=(width, height),
                compression=nl.enums.Compression.raw,
            )

            # 设置分辨率为 300 DPI
            from config import processing_config
            import struct
            from pytoshop.image_resources import GenericImageResourceBlock

            dpi = processing_config.DIE_ELEMENT_DEFAULT_DPI
            # DPI 需要转换为 Fixed point: dpi * 65536
            h_res = int(dpi * 65536)
            v_res = int(dpi * 65536)

            # 构建 Resolution Info 数据
            # h_res_unit: 1 = pixels per inch, width_unit: 2 = inches
            # v_res_unit: 1 = pixels per inch, height_unit: 2 = inches
            res_data = struct.pack('>IHH IHH', h_res, 1, 2, v_res, 1, 2)

            # 创建 Resolution Info block (Resource ID = 1005)
            res_block = GenericImageResourceBlock(resource_id=1005, name='', data=res_data)

            # 添加到 image_resources
            psdfile.image_resources._blocks.append(res_block)

            # 写入文件
            with open(output_path, 'wb') as f:
                psdfile.write(f)

            return True

        except Exception as e:
            print(f"❌ 构建PSD失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_preview_png(self, output_path: str, canvas_size: tuple, layers: List[Dict]) -> bool:
        """
        生成整体预览PNG

        Args:
            output_path: 输出文件路径
            canvas_size: 画布尺寸 (width, height)
            layers: 图层列表 [{name, image}]

        Returns:
            是否成功
        """
        try:
            width, height = canvas_size

            # 创建白色背景
            preview = Image.new('RGBA', (width, height), (255, 255, 255, 255))

            # 逐层合成
            for layer_data in layers:
                layer_img = layer_data['image']
                if layer_img.mode != 'RGBA':
                    layer_img = layer_img.convert('RGBA')

                # 使用alpha通道合成
                preview.paste(layer_img, (0, 0), layer_img)

            # 转换为RGB保存（PNG不需要alpha）
            preview_rgb = preview.convert('RGB')
            preview_rgb.save(output_path, 'PNG')

            return True

        except Exception as e:
            print(f"❌ 生成预览图失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_all_arrangements(self) -> List[Dict]:
        """获取所有排版成品"""
        arrangements = self._load_index()
        # 按创建时间倒序排列
        arrangements.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        return arrangements

    def get_arrangement(self, arrangement_id: str) -> Optional[Dict]:
        """获取单个排版成品"""
        arrangements = self._load_index()
        for arr in arrangements:
            if arr['id'] == arrangement_id:
                return arr
        return None

    def delete_arrangement(self, arrangement_id: str) -> bool:
        """
        删除排版成品

        Args:
            arrangement_id: 排版成品ID

        Returns:
            是否删除成功
        """
        try:
            arrangement = self.get_arrangement(arrangement_id)
            if not arrangement:
                return False

            # 删除PSD文件
            psd_path = self.storage_dir / arrangement['psdFileName']
            if psd_path.exists():
                os.unlink(psd_path)
                print(f"✓ 已删除PSD: {arrangement['psdFileName']}")

            # 删除预览图
            if arrangement.get('previewFileName'):
                preview_path = self.storage_dir / arrangement['previewFileName']
                if preview_path.exists():
                    os.unlink(preview_path)
                    print(f"✓ 已删除预览图: {arrangement['previewFileName']}")

            # 从索引中删除
            arrangements = self._load_index()
            arrangements = [a for a in arrangements if a['id'] != arrangement_id]
            self._save_index(arrangements)

            return True

        except Exception as e:
            print(f"❌ 删除排版成品失败: {e}")
            return False


# 全局实例
print_arrangement_manager = PrintArrangementManager()
