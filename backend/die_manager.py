#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
刀模系统数据管理模块
负责刀模元素和素材的CRUD操作
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid
import math
from PIL import Image
from config import processing_config


class DieManager:
    """刀模系统管理器"""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.die_elements_dir = self.storage_dir / "die_elements"
        self.materials_dir = self.die_elements_dir / "materials"
        self.elements_file = self.die_elements_dir / "elements.json"
        self.materials_file = self.die_elements_dir / "materials.json"

        # 确保目录存在
        self.die_elements_dir.mkdir(parents=True, exist_ok=True)
        self.materials_dir.mkdir(parents=True, exist_ok=True)

        # 初始化JSON文件
        if not self.elements_file.exists():
            self._save_json(self.elements_file, [])
        if not self.materials_file.exists():
            self._save_json(self.materials_file, [])

    @staticmethod
    def _cm_to_pixels(size_cm: Dict[str, float]) -> Dict[str, int]:
        """
        将厘米尺寸转换为像素尺寸（使用全局默认DPI）

        公式: 像素 = ceil(cm * 10 / 25.4 * DPI)
        向上取整确保像素尺寸足够，0.1按1处理

        Args:
            size_cm: {"width": cm, "height": cm}

        Returns:
            {"width": px, "height": px}
        """
        dpi = processing_config.DIE_ELEMENT_DEFAULT_DPI
        width_px = math.ceil(size_cm['width'] * 10 / 25.4 * dpi)
        height_px = math.ceil(size_cm['height'] * 10 / 25.4 * dpi)
        return {
            "width": int(width_px),
            "height": int(height_px)
        }

    def _save_json(self, file_path: Path, data):
        """保存JSON数据"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, file_path: Path):
        """加载JSON数据"""
        if not file_path.exists():
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ========== 刀模元素管理 ==========

    def _cut_sizes_equal(self, size_a: Dict[str, float], size_b: Dict[str, float], tol: float = 1e-6) -> bool:
        """判断两个裁切尺寸是否相同（考虑旋转：a×b 与 b×a 视为相同）"""
        w_a = size_a.get("width", 0)
        h_a = size_a.get("height", 0)
        w_b = size_b.get("width", 0)
        h_b = size_b.get("height", 0)

        # 检查无旋转情况：width_a == width_b AND height_a == height_b
        no_rotation = (
            math.isclose(w_a, w_b, abs_tol=tol) and
            math.isclose(h_a, h_b, abs_tol=tol)
        )

        # 检查旋转90度情况：width_a == height_b AND height_a == width_b
        rotated_90 = (
            math.isclose(w_a, h_b, abs_tol=tol) and
            math.isclose(h_a, w_b, abs_tol=tol)
        )

        return no_rotation or rotated_90

    def create_element(self, name: str, cut_size: Dict[str, float],
                      reference_size: Dict[str, float]) -> Dict:
        """创建刀模元素

        Args:
            name: 元素名称
            cut_size: 裁切尺寸 {"width": float, "height": float} (cm)
            reference_size: 参考尺寸 {"width": float, "height": float} (cm)

        Returns:
            创建的元素数据
        """
        element_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 计算像素尺寸
        cut_size_pixels = self._cm_to_pixels(cut_size)
        reference_size_pixels = self._cm_to_pixels(reference_size)

        element = {
            "id": element_id,
            "name": name,
            "cutSize": cut_size,
            "cutSizePixels": cut_size_pixels,
            "referenceSize": reference_size,
            "referenceSizePixels": reference_size_pixels,
            "createdAt": now,
            "updatedAt": now
        }

        # 加载现有元素
        elements = self._load_json(self.elements_file)

        # 校验是否存在相同尺寸
        for existing in elements:
            if self._cut_sizes_equal(existing.get("cutSize", {}), cut_size):
                raise ValueError("已存在裁切尺寸完全相同的刀模元素，请勿重复创建")

        elements.append(element)

        # 保存
        self._save_json(self.elements_file, elements)

        # 创建元素素材目录
        element_materials_dir = self.materials_dir / element_id
        element_materials_dir.mkdir(parents=True, exist_ok=True)

        return element

    def get_elements(self) -> List[Dict]:
        """获取所有刀模元素"""
        return self._load_json(self.elements_file)

    def get_element(self, element_id: str) -> Optional[Dict]:
        """获取单个刀模元素"""
        elements = self.get_elements()
        for element in elements:
            if element["id"] == element_id:
                return element
        return None

    def update_element(self, element_id: str, name: Optional[str] = None,
                      cut_size: Optional[Dict[str, float]] = None,
                      reference_size: Optional[Dict[str, float]] = None) -> Optional[Dict]:
        """更新刀模元素

        Returns:
            更新后的元素数据，如果元素不存在返回None
        """
        elements = self._load_json(self.elements_file)

        for i, element in enumerate(elements):
            if element["id"] == element_id:
                # 如果要更新裁切尺寸，先校验是否重复
                if cut_size is not None:
                    for other in elements:
                        if other["id"] != element_id and self._cut_sizes_equal(other.get("cutSize", {}), cut_size):
                            raise ValueError("已存在裁切尺寸完全相同的刀模元素，无法变更为该尺寸")

                # 更新字段
                if name is not None:
                    element["name"] = name
                if cut_size is not None:
                    element["cutSize"] = cut_size
                    element["cutSizePixels"] = self._cm_to_pixels(cut_size)
                if reference_size is not None:
                    element["referenceSize"] = reference_size
                    element["referenceSizePixels"] = self._cm_to_pixels(reference_size)
                element["updatedAt"] = datetime.now().isoformat()

                # 保存
                self._save_json(self.elements_file, elements)
                return element

        return None

    def delete_element(self, element_id: str) -> bool:
        """删除刀模元素及其所有素材

        Returns:
            是否删除成功
        """
        elements = self._load_json(self.elements_file)

        # 查找并删除元素
        new_elements = [e for e in elements if e["id"] != element_id]
        if len(new_elements) == len(elements):
            return False  # 元素不存在

        # 删除元素素材目录
        element_materials_dir = self.materials_dir / element_id
        if element_materials_dir.exists():
            shutil.rmtree(element_materials_dir)

        # 删除素材记录
        materials = self._load_json(self.materials_file)
        new_materials = [m for m in materials if m["elementId"] != element_id]
        self._save_json(self.materials_file, new_materials)

        # 保存元素列表
        self._save_json(self.elements_file, new_elements)

        return True

    # ========== 刀模素材管理 ==========

    def _process_image_for_material(self, image_path: Path, output_path: Path,
                                    cut_size_pixels: Dict[str, int],
                                    rotation_angle: float = 0) -> Tuple[bool, str]:
        """
        处理图片：按照元素的精确像素尺寸进行裁切和旋转

        Args:
            image_path: 输入图片路径
            output_path: 输出图片路径
            cut_size_pixels: 裁切像素尺寸 {"width": px, "height": px}
            rotation_angle: 旋转角度（度）

        Returns:
            (成功标志, 错误信息)
        """
        try:
            with Image.open(image_path) as img:
                # 确保图片是RGBA模式
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                img_width, img_height = img.size

                # 获取需要的像素尺寸
                required_width = cut_size_pixels['width']
                required_height = cut_size_pixels['height']

                # 考虑旋转：如果旋转90或270度，需要交换宽高
                if rotation_angle in [90, 270, -90, -270]:
                    required_width, required_height = required_height, required_width

                # 验证图片尺寸是否足够
                if img_width < required_width or img_height < required_height:
                    return False, (
                        f"图片尺寸不足: 需要至少 {required_width}×{required_height} 像素, "
                        f"当前图片为 {img_width}×{img_height} 像素"
                    )

                # 计算居中裁切的起始坐标
                left = (img_width - required_width) // 2
                top = (img_height - required_height) // 2
                right = left + required_width
                bottom = top + required_height

                # 执行裁切
                img_cropped = img.crop((left, top, right, bottom))

                # 执行旋转（逆时针）
                if rotation_angle != 0:
                    img_cropped = img_cropped.rotate(rotation_angle, expand=True)

                # 保存为PNG
                img_cropped.save(output_path, "PNG")
                return True, ""

        except Exception as e:
            return False, f"图片处理失败: {str(e)}"

    def add_material(self, element_id: str, file_name: str,
                    file_path: str, temp_image_path: Path,
                    rotation_angle: float = 0) -> Optional[Dict]:
        """添加刀模素材

        Args:
            element_id: 元素ID
            file_name: 文件名
            file_path: 文件路径（相对于materials目录）
            temp_image_path: 临时上传图片的完整路径
            rotation_angle: 旋转角度 (度)

        Returns:
            创建的素材数据，如果元素不存在返回None
        """
        # 检查元素是否存在
        element = self.get_element(element_id)
        if not element:
            return None

        # 处理图片并保存
        output_full_path = self.die_elements_dir / file_path

        process_success, process_msg = self._process_image_for_material(
            image_path=temp_image_path,
            output_path=output_full_path,
            cut_size_pixels=element["cutSizePixels"],
            rotation_angle=rotation_angle
        )

        if not process_success:
            print(f"图片处理失败: {process_msg}")
            return None

        material_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        material = {
            "id": material_id,
            "elementId": element_id,
            "elementName": element["name"],
            "fileName": file_name,
            "filePath": file_path,
            "cutSize": element["cutSize"],
            "referenceSize": element["referenceSize"],
            "createdAt": now
        }

        # 加载现有素材
        materials = self._load_json(self.materials_file)
        materials.append(material)

        # 保存
        self._save_json(self.materials_file, materials)

        return material

    def get_materials(self, element_id: Optional[str] = None) -> List[Dict]:
        """获取刀模素材

        Args:
            element_id: 可选，按元素ID过滤

        Returns:
            素材列表
        """
        materials = self._load_json(self.materials_file)

        if element_id:
            materials = [m for m in materials if m["elementId"] == element_id]

        return materials

    def get_materials_grouped(self) -> Dict[str, Dict]:
        """获取按元素分组的素材

        Returns:
            格式: {
                "element_id": {
                    "elementName": str,
                    "cutSize": dict,
                    "referenceSize": dict,
                    "materials": [...]
                }
            }
        """
        materials = self._load_json(self.materials_file)
        grouped = {}

        for material in materials:
            element_id = material["elementId"]
            if element_id not in grouped:
                grouped[element_id] = {
                    "elementName": material["elementName"],
                    "cutSize": material["cutSize"],
                    "referenceSize": material["referenceSize"],
                    "materials": []
                }
            grouped[element_id]["materials"].append(material)

        return grouped

    def get_material(self, material_id: str) -> Optional[Dict]:
        """获取单个素材"""
        materials = self._load_json(self.materials_file)
        for material in materials:
            if material["id"] == material_id:
                return material
        return None

    def delete_material(self, material_id: str) -> bool:
        """删除刀模素材

        Returns:
            是否删除成功
        """
        materials = self._load_json(self.materials_file)

        # 查找素材
        material = None
        for m in materials:
            if m["id"] == material_id:
                material = m
                break

        if not material:
            return False

        # 删除文件
        file_path = self.die_elements_dir / material["filePath"]
        if file_path.exists():
            os.unlink(file_path)

        # 删除记录
        new_materials = [m for m in materials if m["id"] != material_id]
        self._save_json(self.materials_file, new_materials)

        return True

    def get_material_file_path(self, material_id: str) -> Optional[Path]:
        """获取素材文件的完整路径"""
        material = self.get_material(material_id)
        if not material:
            return None

        file_path = self.die_elements_dir / material["filePath"]
        if not file_path.exists():
            return None

        return file_path


# 全局实例
die_manager = DieManager()
