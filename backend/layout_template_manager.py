"""
布局模版管理器
负责保存、加载、删除布局模版，以及生成预览图
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import psd_layout_parser
import die_manager
from psd_layout_processor import psd_layout_processor


class LayoutTemplateManager:
    def __init__(self, storage_dir: str = "storage/layout_templates"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def create_template(self, name: str, paper_size: str, paper_orientation: str,
                       elements: List[Dict], preview_image_base64: str = None) -> Dict:
        """创建新模版"""
        template_id = str(uuid.uuid4())

        # 生成预览图
        if not preview_image_base64:
            preview_image_base64 = self._generate_preview(
                paper_size, paper_orientation, elements
            )

        template = {
            "id": template_id,
            "name": name,
            "paperSize": paper_size,
            "paperOrientation": paper_orientation,
            "elements": elements,
            "previewImage": preview_image_base64,
            "createdAt": datetime.now().isoformat()
        }

        # 保存到文件
        template_path = os.path.join(self.storage_dir, f"{template_id}.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        return template

    def get_all_templates(self) -> List[Dict]:
        """获取所有模版"""
        templates = []

        if not os.path.exists(self.storage_dir):
            return templates

        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                template_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template = json.load(f)
                        templates.append(template)
                except Exception as e:
                    print(f"Error loading template {filename}: {e}")

        # 按创建时间倒序排序
        templates.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        return templates

    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取单个模版"""
        template_path = os.path.join(self.storage_dir, f"{template_id}.json")

        if not os.path.exists(template_path):
            return None

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading template {template_id}: {e}")
            return None

    def delete_template(self, template_id: str) -> bool:
        """删除模版（包括关联的布局PSD文件）"""
        template_path = os.path.join(self.storage_dir, f"{template_id}.json")

        if not os.path.exists(template_path):
            return False

        try:
            # 读取模板信息，获取布局PSD文件名
            template = self.get_template(template_id)

            # 删除模板JSON文件
            os.remove(template_path)

            # 删除布局PSD文件（如果存在）
            if template and template.get('layoutPsdFileName'):
                layout_psd_path = os.path.join(self.storage_dir, template['layoutPsdFileName'])
                if os.path.exists(layout_psd_path):
                    os.remove(layout_psd_path)
                    print(f"✓ 已删除布局PSD: {template['layoutPsdFileName']}")

            return True
        except Exception as e:
            print(f"Error deleting template {template_id}: {e}")
            return False

    def create_from_psd(self, psd_file_path: str, name: str = None) -> Dict:
        """
        从 PSD 文件创建布局模板

        Args:
            psd_file_path: PSD 文件路径
            name: 模板名称（可选，默认使用文件名）

        Returns:
            模板对象

        Raises:
            ValueError: 当图层无法匹配到刀模元素时
        """
        # 1. 解析 PSD
        psd_info = psd_layout_parser.parse_psd_file(psd_file_path)

        # 2. 获取所有刀模元素
        die_elements = die_manager.DieManager().get_elements()

        # 3. 匹配图层
        match_result = psd_layout_parser.match_layers_to_die_elements(
            psd_info['layers'],
            die_elements
        )

        # 4. 检查是否全部匹配
        if not match_result['success']:
            raise ValueError({
                'message': '部分图层无法匹配到刀模元素',
                'unmatched_layers': match_result['unmatched_layers']
            })

        # 5. 生成模板数据
        template_id = str(uuid.uuid4())
        elements = []

        for matched in match_result['matched']:
            elements.append({
                'id': str(uuid.uuid4()),
                'elementId': matched['element_id'],
                'elementName': matched['element_name'],
                'cutSize': matched['cut_size'],
                'position': matched['position'],
                'rotation': matched['rotation'],
                'layerIndex': matched['layer_index']
            })

        # 6. 生成白色填充的布局PSD
        layout_psd_filename = f"{template_id}_layout.psd"
        layout_psd_path = os.path.join(self.storage_dir, layout_psd_filename)

        print(f"\n🎨 生成白色填充布局PSD...")
        layout_success = psd_layout_processor.create_white_filled_layout_psd(
            input_psd_path=psd_file_path,
            output_psd_path=layout_psd_path,
            elements=elements  # 传递元素列表，用于设置图层名称
        )

        if not layout_success:
            print(f"⚠️  布局PSD生成失败，但模板仍会创建")
            layout_psd_filename = None

        # 7. 生成预览图
        preview_image = psd_layout_parser.generate_preview_image(
            psd_info['canvas_size'],
            elements
        )

        # 8. 确定模板名称
        if not name:
            name = os.path.splitext(os.path.basename(psd_file_path))[0]

        # 9. 保存模板
        template = {
            'id': template_id,
            'name': name,
            'psdFileName': os.path.basename(psd_file_path),
            'layoutPsdFileName': layout_psd_filename,  # 新增：布局PSD文件名
            'canvasSize': psd_info['canvas_size'],
            'elements': elements,
            'previewImage': preview_image,
            'createdAt': datetime.now().isoformat()
        }

        # 保存到文件
        template_path = os.path.join(self.storage_dir, f"{template_id}.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        return template

    def clear_old_format_templates(self):
        """
        清空旧格式的模板数据
        （旧格式使用 paperSize 和 paperOrientation，新格式使用 canvasSize）
        """
        if not os.path.exists(self.storage_dir):
            return

        cleared_count = 0
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                template_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template = json.load(f)

                    # 检查是否为旧格式（有 paperSize 而没有 canvasSize）
                    if 'paperSize' in template and 'canvasSize' not in template:
                        os.remove(template_path)
                        cleared_count += 1
                        print(f"Cleared old format template: {template.get('name', filename)}")
                except Exception as e:
                    print(f"Error processing template {filename}: {e}")

        if cleared_count > 0:
            print(f"Total cleared {cleared_count} old format template(s)")
        else:
            print("No old format templates found")

    def _generate_preview(self, paper_size: str, paper_orientation: str,
                         elements: List[Dict]) -> str:
        """生成模版预览图"""
        # 纸张尺寸（mm）
        PAPER_SIZES = {
            'A3': {'width': 420, 'height': 297},
            'A4': {'width': 297, 'height': 210}
        }

        paper = PAPER_SIZES.get(paper_size, PAPER_SIZES['A4'])

        # 如果是纵向，交换宽高
        if paper_orientation == 'portrait':
            paper = {'width': paper['height'], 'height': paper['width']}

        # 预览图缩放比例：1mm = 2px
        MM_TO_PX = 2
        width_px = int(paper['width'] * MM_TO_PX)
        height_px = int(paper['height'] * MM_TO_PX)

        # 创建图片
        img = Image.new('RGB', (width_px, height_px), color='white')
        draw = ImageDraw.Draw(img)

        # 绘制纸张边框（黑色）
        draw.rectangle([0, 0, width_px-1, height_px-1], outline='black', width=2)

        # 绘制出血线（红色虚线）
        BLEED_MARGIN = 5  # mm
        bleed_px = int(BLEED_MARGIN * MM_TO_PX)

        # 虚线效果：画多个短线段
        dash_length = 5
        for i in range(0, width_px, dash_length * 2):
            draw.line([(bleed_px, i), (bleed_px, min(i + dash_length, height_px))],
                     fill='red', width=1)
            draw.line([(width_px - bleed_px, i), (width_px - bleed_px, min(i + dash_length, height_px))],
                     fill='red', width=1)

        for i in range(0, height_px, dash_length * 2):
            draw.line([(i, bleed_px), (min(i + dash_length, width_px), bleed_px)],
                     fill='red', width=1)
            draw.line([(i, height_px - bleed_px), (min(i + dash_length, width_px), height_px - bleed_px)],
                     fill='red', width=1)

        # 尝试加载字体
        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 10)
        except:
            font = ImageFont.load_default()

        # 绘制元素框
        for element in elements:
            x = int(element['x'] * MM_TO_PX)
            y = int(element['y'] * MM_TO_PX)
            w = int(element['cutSize']['width'] * 10 * MM_TO_PX)  # cm转mm再转px
            h = int(element['cutSize']['height'] * 10 * MM_TO_PX)
            rotation = element.get('rotation', 0)

            # 考虑旋转后的尺寸
            if rotation == 90 or rotation == 270:
                w, h = h, w

            # 绘制蓝色边框
            draw.rectangle([x, y, x + w, y + h], outline='blue', width=1)

            # 绘制元素名称（居中）
            name = element.get('elementName', '')
            # 简单居中（不考虑文字实际宽度）
            text_x = x + w // 2 - len(name) * 3
            text_y = y + h // 2 - 5
            draw.text((text_x, text_y), name, fill='blue', font=font)

        # 转换为Base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"
