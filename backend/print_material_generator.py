"""
打印素材生成器
负责根据模版和素材映射生成打印PDF及预览图
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import base64
from io import BytesIO


class PrintMaterialGenerator:
    def __init__(self, storage_dir: str = "storage/print_materials",
                 materials_dir: str = "storage/die_materials"):
        self.storage_dir = storage_dir
        self.materials_dir = materials_dir
        os.makedirs(storage_dir, exist_ok=True)

    def create_print_material(self, name: str, template: Dict,
                            material_mappings: List[Dict]) -> Dict:
        """创建打印素材（生成PDF和预览图）"""
        material_id = str(uuid.uuid4())

        # 生成PDF
        pdf_filename = f"{material_id}.pdf"
        pdf_path = os.path.join(self.storage_dir, pdf_filename)

        # 生成预览图
        preview_base64 = self._generate_pdf_and_preview(
            pdf_path, template, material_mappings
        )

        # 获取PDF文件大小
        file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0

        # 创建元数据
        print_material = {
            "id": material_id,
            "name": name,
            "templateId": template['id'],
            "templateName": template['name'],
            "pdfFileName": pdf_filename,
            "pdfFilePath": pdf_path,
            "previewImage": preview_base64,
            "fileSize": file_size,
            "materialMappings": material_mappings,
            "createdAt": datetime.now().isoformat()
        }

        # 保存元数据
        metadata_path = os.path.join(self.storage_dir, f"{material_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(print_material, f, ensure_ascii=False, indent=2)

        return print_material

    def get_all_print_materials(self) -> List[Dict]:
        """获取所有打印素材"""
        materials = []

        if not os.path.exists(self.storage_dir):
            return materials

        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                material_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(material_path, 'r', encoding='utf-8') as f:
                        material = json.load(f)
                        materials.append(material)
                except Exception as e:
                    print(f"Error loading print material {filename}: {e}")

        # 按创建时间倒序排序
        materials.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        return materials

    def get_print_material(self, material_id: str) -> Optional[Dict]:
        """获取单个打印素材"""
        material_path = os.path.join(self.storage_dir, f"{material_id}.json")

        if not os.path.exists(material_path):
            return None

        try:
            with open(material_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading print material {material_id}: {e}")
            return None

    def delete_print_material(self, material_id: str) -> bool:
        """删除打印素材"""
        metadata_path = os.path.join(self.storage_dir, f"{material_id}.json")
        pdf_path = os.path.join(self.storage_dir, f"{material_id}.pdf")

        if not os.path.exists(metadata_path):
            return False

        try:
            # 删除元数据文件
            os.remove(metadata_path)
            # 删除PDF文件
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return True
        except Exception as e:
            print(f"Error deleting print material {material_id}: {e}")
            return False

    def _generate_pdf_and_preview(self, pdf_path: str, template: Dict,
                                  material_mappings: List[Dict]) -> str:
        """生成PDF和预览图"""
        # 获取画布尺寸（支持新旧格式）
        if 'canvasSize' in template:
            # 新格式：直接使用 canvasSize
            width_mm = template['canvasSize']['width']
            height_mm = template['canvasSize']['height']
        else:
            # 旧格式：使用 paperSize 和 paperOrientation
            PAPER_SIZES = {
                'A3': {'width': 420, 'height': 297},
                'A4': {'width': 297, 'height': 210}
            }
            paper_size = template['paperSize']
            paper_orientation = template['paperOrientation']
            paper = PAPER_SIZES.get(paper_size, PAPER_SIZES['A4'])

            # 如果是纵向，交换宽高
            if paper_orientation == 'portrait':
                paper = {'width': paper['height'], 'height': paper['width']}

            width_mm = paper['width']
            height_mm = paper['height']

        # 创建PDF
        c = canvas.Canvas(pdf_path, pagesize=(width_mm * mm, height_mm * mm))

        # 创建预览图（用于生成缩略图）
        MM_TO_PX = 2
        preview_width = int(width_mm * MM_TO_PX)
        preview_height = int(height_mm * MM_TO_PX)
        preview_img = Image.new('RGB', (preview_width, preview_height), color='white')

        # 创建素材ID到文件路径的映射
        material_map = {m['materialId']: m for m in material_mappings}

        # 遍历模版中的元素
        for element in template['elements']:
            layout_element_id = element['id']

            # 查找对应的素材
            mapping = next((m for m in material_mappings
                          if m['layoutElementId'] == layout_element_id), None)

            if not mapping:
                continue

            material_id = mapping['materialId']
            material_path = os.path.join(self.materials_dir, f"{material_id}.png")

            if not os.path.exists(material_path):
                continue

            # 加载素材图片
            try:
                img = Image.open(material_path)

                # 元素位置和尺寸（mm）- 支持新旧格式
                if 'position' in element:
                    # 新格式
                    x_mm = element['position']['x']
                    y_mm = element['position']['y']
                else:
                    # 旧格式
                    x_mm = element['x']
                    y_mm = element['y']

                w_mm = element['cutSize']['width'] * 10  # cm转mm
                h_mm = element['cutSize']['height'] * 10
                rotation = element.get('rotation', 0)

                # PDF坐标系：左下角为原点，向上为正
                # 需要转换Y坐标
                pdf_y_mm = height_mm - y_mm - h_mm

                # 处理旋转（仅支持90度逆时针旋转）
                if rotation == 90:
                    # 使用PIL预旋转图像（顺时针90度，因为PDF需要）
                    img_rotated = img.rotate(-90, expand=True)

                    # 保存临时旋转图像
                    import tempfile
                    temp_path = tempfile.mktemp(suffix='.png')
                    img_rotated.save(temp_path)

                    # 绘制到PDF（注意宽高交换）
                    c.drawImage(temp_path, x_mm * mm, pdf_y_mm * mm,
                              width=h_mm * mm, height=w_mm * mm,
                              preserveAspectRatio=False)

                    # 清理临时文件
                    os.remove(temp_path)

                    # 绘制到预览图（使用旋转后的图像）
                    preview_x = int(x_mm * MM_TO_PX)
                    preview_y = int(y_mm * MM_TO_PX)
                    preview_w = int(h_mm * MM_TO_PX)  # 注意宽高交换
                    preview_h = int(w_mm * MM_TO_PX)

                    img_resized = img_rotated.resize((preview_w, preview_h), Image.LANCZOS)
                    preview_img.paste(img_resized, (preview_x, preview_y))

                else:
                    # 无旋转，直接绘制
                    c.drawImage(material_path, x_mm * mm, pdf_y_mm * mm,
                              width=w_mm * mm, height=h_mm * mm,
                              preserveAspectRatio=False)

                    # 绘制到预览图
                    preview_x = int(x_mm * MM_TO_PX)
                    preview_y = int(y_mm * MM_TO_PX)
                    preview_w = int(w_mm * MM_TO_PX)
                    preview_h = int(h_mm * MM_TO_PX)

                    # 调整图片大小并粘贴到预览图
                    img_resized = img.resize((preview_w, preview_h), Image.LANCZOS)
                    preview_img.paste(img_resized, (preview_x, preview_y))

            except Exception as e:
                print(f"Error processing material {material_id}: {e}")

        # 保存PDF
        c.save()

        # 绘制预览图边框
        draw = ImageDraw.Draw(preview_img)
        draw.rectangle([0, 0, preview_width-1, preview_height-1], outline='black', width=2)

        # 转换预览图为Base64
        buffer = BytesIO()
        preview_img.save(buffer, format='PNG')
        preview_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{preview_base64}"
