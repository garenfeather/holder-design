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
from PIL import Image


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

        element = {
            "id": element_id,
            "name": name,
            "cutSize": cut_size,
            "referenceSize": reference_size,
            "createdAt": now,
            "updatedAt": now
        }

        # 加载现有元素
        elements = self._load_json(self.elements_file)
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
                # 更新字段
                if name is not None:
                    element["name"] = name
                if cut_size is not None:
                    element["cutSize"] = cut_size
                if reference_size is not None:
                    element["referenceSize"] = reference_size
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
                                    cut_size_cm: Dict[str, float], reference_size_cm: Dict[str, float],
                                    rotation_angle: float = 0) -> Tuple[bool, str]:
        """
        处理图片，包括裁切、旋转，并保存为PNG。
        假定输入图片已是正方形，根据cut_size和reference_size（单位cm）计算并裁切。
        这里简化处理，将图片直接视为与参考尺寸对应，然后根据裁切尺寸进行中心裁切。
        """
        try:
            with Image.open(image_path) as img:
                # 确保图片是RGB模式
                if img.mode != 'RGB' and img.mode != 'RGBA':
                    img = img.convert('RGBA')

                # 将CM尺寸转换为像素（假设图片DPI为300，或者直接按比例计算）
                # 这里简化：假设输入图片是与参考尺寸按比例匹配的
                # 所以我们计算裁切区域的比例，然后应用到图片上

                # 假设前端传递的图片已经按照reference_size进行了缩放或处理
                # 这里我们直接根据 cut_size_cm 和 reference_size_cm 的比例进行裁切
                ref_width_cm = reference_size_cm['width']
                ref_height_cm = reference_size_cm['height']
                cut_width_cm = cut_size_cm['width']
                cut_height_cm = cut_size_cm['height']

                if ref_width_cm == 0 or ref_height_cm == 0:
                    return False, "参考尺寸不能为0"

                # 计算裁切框占参考框的比例
                cut_ratio_w = cut_width_cm / ref_width_cm
                cut_ratio_h = cut_height_cm / ref_height_cm

                # 根据图片实际尺寸和裁切比例计算裁切像素
                img_width, img_height = img.size

                # 裁切的像素尺寸
                crop_width_px = int(img_width * cut_ratio_w)
                crop_height_px = int(img_height * cut_ratio_h)

                # 计算中心裁切的起始坐标
                left = (img_width - crop_width_px) / 2
                top = (img_height - crop_height_px) / 2
                right = (img_width + crop_width_px) / 2
                bottom = (img_height + crop_height_px) / 2

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
            cut_size_cm=element["cutSize"],
            reference_size_cm=element["referenceSize"],
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
