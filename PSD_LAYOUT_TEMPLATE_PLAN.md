# PSD 布局模板与排版打印功能技术方案

## 一、功能概述

### 1.1 核心需求
1. **布局模板 PSD 上传**：上传 PSD 文件，自动提取图层信息并匹配刀模元素
2. **模板预览与使用**：白色画布展示模板结构，点击使用跳转排版
3. **排版打印编辑器**：双列布局，左侧素材选择，右侧画布排版（支持缩放）
4. **PDF 生成下载**：保存排版结果为 PDF 和预览图

### 1.2 技术栈
- **后端**：Flask + psd-tools + Pillow + reportlab
- **前端**：React + TypeScript + Tailwind CSS

---

## 二、数据结构设计

### 2.1 布局模板数据结构

**存储位置**: `backend/storage/layout_templates/templates.json`

```json
{
  "id": "uuid",
  "name": "春节套装布局",
  "psdFileName": "spring_layout.psd",
  "canvasSize": {
    "width": 297,
    "height": 210
  },
  "elements": [
    {
      "id": "element-instance-uuid-1",
      "elementId": "die-element-uuid",
      "elementName": "蝴蝶结",
      "cutSize": {
        "width": 5.72,
        "height": 7.61
      },
      "position": {
        "x": 20.5,
        "y": 30.2
      },
      "rotation": 0,
      "layerIndex": 0
    }
  ],
  "previewImage": "data:image/png;base64,...",
  "createdAt": "2025-11-07T10:00:00"
}
```

**字段说明**：
- `canvasSize`: 画布尺寸（mm）
- `elements[].position`: 元素位置（mm，相对画布左上角）
- `elements[].rotation`: 0=无旋转，90=逆时针90°
- `elements[].cutSize`: 刀模裁切尺寸（cm）

### 2.2 打印素材存储结构

**简化设计**：不使用 JSON 索引，直接文件存储

```
backend/storage/print_materials/
├── {uuid}.pdf           # PDF 文件
└── {uuid}_preview.png   # 预览图（小图）
```

**文件命名规则**：
- UUID 作为文件名主体
- PDF 文件用于下载
- 预览图用于列表展示（建议尺寸：400x300px）

**元数据获取**：
- 通过扫描目录获取文件列表
- 从文件系统读取创建时间、大小等信息
- 预览图直接从 PNG 文件读取

---

## 三、API 接口设计

### 3.1 布局模板相关

| 方法 | 路径 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| POST | `/api/layout-templates/upload-psd` | 上传PSD并创建模板 | FormData(psd文件) | 模板对象 或 错误详情 |
| GET | `/api/layout-templates` | 获取模板列表 | - | 模板数组 |
| GET | `/api/layout-templates/:id` | 获取单个模板 | id | 模板对象 |
| DELETE | `/api/layout-templates/:id` | 删除模板 | id | {success: true} |

### 3.2 打印素材相关

| 方法 | 路径 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| POST | `/api/print-materials/generate` | 生成打印素材 | {templateId, materialMappings} | {pdfId, previewUrl} |
| GET | `/api/print-materials` | 获取打印素材列表 | - | 文件信息数组 |
| GET | `/api/print-materials/:id/pdf` | 下载PDF | id | PDF文件流 |
| GET | `/api/print-materials/:id/preview` | 获取预览图 | id | PNG图片 |
| DELETE | `/api/print-materials/:id` | 删除打印素材 | id | {success: true} |

---

## 四、核心模块设计

### 4.1 PSD 解析模块（`psd_layout_parser.py`）

#### 函数1：`parse_psd_file(psd_path) -> dict`

**功能**：提取 PSD 画布和图层信息

**实现要点**：
```python
from psd_tools import PSDImage

def parse_psd_file(psd_path):
    psd = PSDImage.open(psd_path)

    # 获取画布尺寸（像素）
    canvas_width_px = psd.width
    canvas_height_px = psd.height
    dpi = psd.header.dpi or (72, 72)  # 默认72 DPI

    # 转换为 mm
    canvas_width_mm = px_to_mm(canvas_width_px, dpi[0])
    canvas_height_mm = px_to_mm(canvas_height_px, dpi[1])

    # 提取所有图层
    layers = []
    for idx, layer in enumerate(psd):
        if not layer.is_group():  # 只处理图层，不处理组
            bbox = layer.bbox  # (left, top, right, bottom) 像素
            if bbox:
                width_px = bbox[2] - bbox[0]
                height_px = bbox[3] - bbox[1]

                layers.append({
                    'index': idx,
                    'bounds': {
                        'x': px_to_mm(bbox[0], dpi[0]),
                        'y': px_to_mm(bbox[1], dpi[1]),
                        'width': px_to_mm(width_px, dpi[0]),
                        'height': px_to_mm(height_px, dpi[1])
                    }
                })

    return {
        'canvas_size': {
            'width': canvas_width_mm,
            'height': canvas_height_mm
        },
        'layers': layers,
        'dpi': dpi
    }
```

**单位转换**：
```python
def px_to_mm(px, dpi=72):
    """像素转毫米"""
    inches = px / dpi
    return inches * 25.4

def cm_to_mm(cm):
    """厘米转毫米"""
    return cm * 10
```

---

#### 函数2：`match_layers_to_die_elements(layers, die_elements) -> dict`

**功能**：匹配图层与刀模元素（基于裁切尺寸）

**匹配规则**：
1. **单位统一**：将刀模元素的 `cutSize`（cm）转换为 mm
2. **容差匹配**：允许 ±0.5mm 误差
3. **旋转检测**：
   - 先尝试无旋转匹配（layer_w ≈ elem_w, layer_h ≈ elem_h）
   - 再尝试90°旋转匹配（layer_w ≈ elem_h, layer_h ≈ elem_w）

**实现逻辑**：
```python
TOLERANCE_MM = 0.5

def match_layers_to_die_elements(layers, die_elements):
    matched = []
    unmatched_layers = []

    for layer in layers:
        layer_w = layer['bounds']['width']
        layer_h = layer['bounds']['height']

        found = False
        for element in die_elements:
            # 刀模元素尺寸（cm 转 mm）
            elem_w = element['cutSize']['width'] * 10
            elem_h = element['cutSize']['height'] * 10

            # 尝试无旋转匹配
            if (abs(layer_w - elem_w) < TOLERANCE_MM and
                abs(layer_h - elem_h) < TOLERANCE_MM):
                matched.append({
                    'layer_index': layer['index'],
                    'element_id': element['id'],
                    'element_name': element['name'],
                    'rotation': 0,
                    'position': {
                        'x': layer['bounds']['x'],
                        'y': layer['bounds']['y']
                    },
                    'cut_size': element['cutSize']
                })
                found = True
                break

            # 尝试90°旋转匹配
            elif (abs(layer_w - elem_h) < TOLERANCE_MM and
                  abs(layer_h - elem_w) < TOLERANCE_MM):
                matched.append({
                    'layer_index': layer['index'],
                    'element_id': element['id'],
                    'element_name': element['name'],
                    'rotation': 90,
                    'position': {
                        'x': layer['bounds']['x'],
                        'y': layer['bounds']['y']
                    },
                    'cut_size': element['cutSize']
                })
                found = True
                break

        if not found:
            unmatched_layers.append({
                'index': layer['index'],
                'size': {
                    'width': round(layer_w, 2),
                    'height': round(layer_h, 2)
                }
            })

    return {
        'success': len(unmatched_layers) == 0,
        'matched': matched,
        'unmatched_layers': unmatched_layers
    }
```

---

#### 函数3：`generate_preview_image(canvas_size, elements) -> str`

**功能**：生成白色画布预览图，显示元素边框和名称

**实现**：
```python
from PIL import Image, ImageDraw, ImageFont

def generate_preview_image(canvas_size, elements):
    # 缩放比例：1mm = 2px
    SCALE = 2
    width_px = int(canvas_size['width'] * SCALE)
    height_px = int(canvas_size['height'] * SCALE)

    # 创建白色画布
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    # 加载字体（小号）
    try:
        font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 12)
    except:
        font = ImageFont.load_default()

    # 绘制每个元素
    for element in elements:
        x = element['position']['x'] * SCALE
        y = element['position']['y'] * SCALE
        w = element['cut_size']['width'] * 10 * SCALE  # cm -> mm -> px
        h = element['cut_size']['height'] * 10 * SCALE

        # 考虑旋转时交换宽高
        if element['rotation'] == 90:
            w, h = h, w

        # 绘制矩形边框（黑色，1px）
        draw.rectangle([x, y, x + w, y + h], outline='black', width=1)

        # 居中绘制元素名称
        text = element['element_name']
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = x + (w - text_w) / 2
        text_y = y + (h - text_h) / 2
        draw.text((text_x, text_y), text, fill='black', font=font)

    # 转换为 Base64
    import io
    import base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_data}"
```

---

### 4.2 布局模板管理器（`layout_template_manager.py`）

#### 修改：新增 `create_from_psd()` 方法

```python
import uuid
from datetime import datetime
from . import psd_layout_parser
from . import die_manager

def create_from_psd(psd_file_path, name):
    """从 PSD 文件创建布局模板"""

    # 1. 解析 PSD
    psd_info = psd_layout_parser.parse_psd_file(psd_file_path)

    # 2. 获取所有刀模元素
    die_elements = die_manager.get_elements()

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

    # 6. 生成预览图
    preview_image = psd_layout_parser.generate_preview_image(
        psd_info['canvas_size'],
        elements
    )

    # 7. 保存模板
    template = {
        'id': template_id,
        'name': name,
        'psdFileName': os.path.basename(psd_file_path),
        'canvasSize': psd_info['canvas_size'],
        'elements': elements,
        'previewImage': preview_image,
        'createdAt': datetime.now().isoformat()
    }

    # 保存到 templates.json
    _save_template(template)

    return template
```

#### 修改：`delete_template()` 级联删除打印素材

```python
def delete_template(template_id):
    """删除模板，同时删除关联的打印素材"""

    # 1. 查找使用该模板的打印素材
    print_materials_dir = 'storage/print_materials'
    template_materials = []

    # 扫描打印素材文件，检查是否关联该模板
    # （由于简化存储，需要通过文件名或其他方式关联）
    # 暂时跳过，后续优化

    # 2. 删除模板记录
    templates = _load_templates()
    templates = [t for t in templates if t['id'] != template_id]
    _save_all_templates(templates)

    return True
```

---

### 4.3 打印素材生成器（`print_material_generator.py`）

#### 主函数：`generate_print_material(template, material_mappings, output_dir) -> dict`

**输入**：
- `template`: 布局模板对象
- `material_mappings`: `{layoutElementId: materialId | None}`
- `output_dir`: 输出目录

**输出**：
```python
{
    'pdf_id': 'uuid',
    'pdf_path': 'storage/print_materials/uuid.pdf',
    'preview_path': 'storage/print_materials/uuid_preview.png',
    'file_size': 1234567  # 字节
}
```

**实现**：
```python
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from PIL import Image

def generate_print_material(template, material_mappings, output_dir):
    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(output_dir, f'{pdf_id}.pdf')
    preview_path = os.path.join(output_dir, f'{pdf_id}_preview.png')

    # 获取画布尺寸
    canvas_width_mm = template['canvasSize']['width']
    canvas_height_mm = template['canvasSize']['height']

    # 创建 PDF
    c = canvas.Canvas(pdf_path, pagesize=(
        canvas_width_mm * mm,
        canvas_height_mm * mm
    ))

    # 创建预览图（PIL）
    PREVIEW_SCALE = 2  # 1mm = 2px
    preview_img = Image.new('RGB', (
        int(canvas_width_mm * PREVIEW_SCALE),
        int(canvas_height_mm * PREVIEW_SCALE)
    ), 'white')
    preview_draw = ImageDraw.Draw(preview_img)

    # 遍历元素并绘制
    for element in template['elements']:
        material_id = material_mappings.get(element['id'])
        if not material_id:
            continue  # 留空

        # 加载素材
        material = die_manager.get_material(material_id)
        material_path = f"storage/die_elements/{material['filePath']}"

        # 计算位置和尺寸
        x_mm = element['position']['x']
        y_mm = element['position']['y']
        w_mm = element['cutSize']['width'] * 10  # cm -> mm
        h_mm = element['cutSize']['height'] * 10

        # PDF 坐标系 Y 轴翻转
        y_pdf = canvas_height_mm - y_mm - h_mm

        # 处理旋转
        if element['rotation'] == 90:
            # 使用 PIL 预旋转图像
            img = Image.open(material_path)
            img_rotated = img.rotate(-90, expand=True)  # 顺时针90°

            # 保存临时旋转图像
            temp_path = f"/tmp/{uuid.uuid4()}.png"
            img_rotated.save(temp_path)

            # 绘制到 PDF（注意宽高交换）
            c.drawImage(temp_path, x_mm * mm, y_pdf * mm, h_mm * mm, w_mm * mm)

            # 清理临时文件
            os.remove(temp_path)

            # 预览图绘制（交换宽高）
            img_resized = img_rotated.resize((
                int(h_mm * PREVIEW_SCALE),
                int(w_mm * PREVIEW_SCALE)
            ))
            preview_img.paste(img_resized, (
                int(x_mm * PREVIEW_SCALE),
                int(y_mm * PREVIEW_SCALE)
            ))
        else:
            # 无旋转直接绘制
            c.drawImage(material_path, x_mm * mm, y_pdf * mm, w_mm * mm, h_mm * mm)

            # 预览图绘制
            img = Image.open(material_path)
            img_resized = img.resize((
                int(w_mm * PREVIEW_SCALE),
                int(h_mm * PREVIEW_SCALE)
            ))
            preview_img.paste(img_resized, (
                int(x_mm * PREVIEW_SCALE),
                int(y_mm * PREVIEW_SCALE)
            ))

    # 保存 PDF
    c.save()

    # 保存预览图（缩小到400x300左右）
    preview_img.thumbnail((400, 300))
    preview_img.save(preview_path)

    # 获取文件大小
    file_size = os.path.getsize(pdf_path)

    return {
        'pdf_id': pdf_id,
        'pdf_path': pdf_path,
        'preview_path': preview_path,
        'file_size': file_size
    }
```

---

## 五、前端组件设计

### 5.1 组件结构

```
App.tsx
└── 刀模 Tab 组
    ├── Tab 1: 刀模元素管理
    ├── Tab 2: 刀模素材与布局
    │   └── DieMaterialAndLayoutManager.tsx
    │       ├── 左列: DieMaterialManager
    │       ├── 中列: 布局模板区
    │       │   ├── LayoutTemplateUpload (新增)
    │       │   ├── 模板卡片列表
    │       │   └── LayoutTemplatePreview (弹窗)
    │       └── 右列: PrintMaterialList (新增)
    └── Tab 3: 排版打印 (新增)
        └── PrintArrangementEditor.tsx
```

---

### 5.2 新增组件详细设计

#### 组件1：`LayoutTemplateUpload.tsx`

```typescript
interface Props {
  onUploadSuccess: () => void;
}

export const LayoutTemplateUpload = ({ onUploadSuccess }: Props) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFileSelect = async (file: File) => {
    // 1. 验证文件
    if (!file.name.endsWith('.psd')) {
      showError('请选择 PSD 文件');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      showError('文件不能超过 50MB');
      return;
    }

    // 2. 上传
    setUploading(true);
    try {
      const result = await api.uploadPsdTemplate(file, (prog) => {
        setProgress(prog);
      });

      showSuccess('上传成功');
      onUploadSuccess();
    } catch (error) {
      // 显示错误详情
      if (error.unmatched_layers) {
        showMatchErrorDialog(error.unmatched_layers);
      } else {
        showError(error.message);
      }
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div>
      <Button onClick={() => fileInputRef.current?.click()}>
        📤 上传 PSD 布局模板
      </Button>
      {uploading && <ProgressBar value={progress} />}
      <input type="file" accept=".psd" hidden ref={fileInputRef} />
    </div>
  );
};
```

---

#### 组件2：`LayoutTemplatePreview.tsx`

```typescript
interface Props {
  template: LayoutTemplate;
  onUseTemplate: (templateId: string) => void;
  onClose: () => void;
}

export const LayoutTemplatePreview = ({ template, onUseTemplate, onClose }: Props) => {
  return (
    <Dialog open onClose={onClose}>
      <div className="max-w-4xl">
        <h2>布局模板预览</h2>

        {/* 预览图 */}
        <div className="my-4 border border-gray-300">
          <img
            src={template.previewImage}
            alt={template.name}
            className="w-full h-auto"
          />
        </div>

        {/* 模板信息 */}
        <div className="text-sm text-gray-600">
          <p>画布尺寸: {template.canvasSize.width}mm × {template.canvasSize.height}mm</p>
          <p>元素数量: {template.elements.length}</p>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button onClick={() => onUseTemplate(template.id)}>
            使用布局模板
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
```

---

#### 组件3：`PrintArrangementEditor.tsx` ⭐

```typescript
interface Props {
  templateId: string;
  onClose: () => void;
}

export const PrintArrangementEditor = ({ templateId, onClose }: Props) => {
  const [template, setTemplate] = useState<LayoutTemplate | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [materialMappings, setMaterialMappings] = useState<Map<string, string>>(new Map());
  const [availableMaterials, setAvailableMaterials] = useState<DieMaterial[]>([]);
  const [scale, setScale] = useState(1);  // 缩放比例

  const canvasRef = useRef<HTMLDivElement>(null);

  // 加载模板
  useEffect(() => {
    api.getLayoutTemplate(templateId).then(setTemplate);
  }, [templateId]);

  // 加载选中元素的素材
  useEffect(() => {
    if (!selectedElementId || !template) return;

    const element = template.elements.find(e => e.id === selectedElementId);
    if (element) {
      api.getDieMaterials({ elementId: element.elementId })
        .then(setAvailableMaterials);
    }
  }, [selectedElementId, template]);

  // 画布点击处理
  const handleCanvasClick = (event: React.MouseEvent) => {
    if (!canvasRef.current || !template) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (event.clientX - rect.left) / scale;
    const clickY = (event.clientY - rect.top) / scale;

    // 计算缩放比例（预览图相对真实画布）
    const imgElement = canvasRef.current.querySelector('img');
    const displayScale = imgElement.clientWidth / template.canvasSize.width;

    // 查找点击的元素
    for (const element of template.elements) {
      const x = element.position.x * displayScale;
      const y = element.position.y * displayScale;
      const w = (element.cutSize.width * 10) * displayScale;
      const h = (element.cutSize.height * 10) * displayScale;

      // 考虑旋转
      const actualW = element.rotation === 90 ? h : w;
      const actualH = element.rotation === 90 ? w : h;

      if (clickX >= x && clickX <= x + actualW &&
          clickY >= y && clickY <= y + actualH) {
        setSelectedElementId(element.id);
        return;
      }
    }
  };

  // 滚轮缩放
  const handleWheel = (event: React.WheelEvent) => {
    event.preventDefault();
    const delta = event.deltaY > 0 ? 0.9 : 1.1;
    setScale(prev => Math.max(0.5, Math.min(3, prev * delta)));
  };

  // 选择素材
  const handleSelectMaterial = (materialId: string) => {
    if (!selectedElementId) return;

    const newMappings = new Map(materialMappings);
    newMappings.set(selectedElementId, materialId);
    setMaterialMappings(newMappings);
  };

  // 清空当前选择
  const handleClearSelection = () => {
    if (!selectedElementId) return;

    const newMappings = new Map(materialMappings);
    newMappings.delete(selectedElementId);
    setMaterialMappings(newMappings);
  };

  // 保存
  const handleSave = async () => {
    const name = prompt('请输入打印素材名称');
    if (!name) return;

    const mappings = Array.from(materialMappings.entries()).map(
      ([layoutElementId, materialId]) => ({ layoutElementId, materialId })
    );

    try {
      await api.generatePrintMaterial({
        templateId,
        materialMappings: mappings
      });

      showSuccess(`打印素材 "${name}" 创建成功`);
      onClose();
    } catch (error) {
      showError(error.message);
    }
  };

  if (!template) return <div>加载中...</div>;

  return (
    <div className="flex h-full">
      {/* 左列：素材选择 */}
      <div className="w-80 border-r p-4 overflow-y-auto">
        <h3 className="font-bold mb-2">素材选择区</h3>

        {selectedElementId && (
          <>
            <p className="text-sm text-gray-600 mb-2">
              当前选中: {template.elements.find(e => e.id === selectedElementId)?.elementName}
            </p>

            <div className="grid grid-cols-3 gap-2 mb-4">
              {availableMaterials.map(material => (
                <div
                  key={material.id}
                  className={`cursor-pointer border-2 ${
                    materialMappings.get(selectedElementId) === material.id
                      ? 'border-blue-500'
                      : 'border-gray-300'
                  }`}
                  onClick={() => handleSelectMaterial(material.id)}
                >
                  <img src={`/api${material.filePath}`} className="w-full h-auto" />
                </div>
              ))}
            </div>

            <Button variant="outline" onClick={handleClearSelection}>
              清空当前选择
            </Button>
          </>
        )}

        {!selectedElementId && (
          <p className="text-gray-500">请点击右侧画布上的元素</p>
        )}
      </div>

      {/* 右列：排版画布 */}
      <div className="flex-1 p-4 overflow-hidden">
        <div className="mb-2 flex justify-between items-center">
          <h3 className="font-bold">模板: {template.name}</h3>
          <span className="text-sm text-gray-500">缩放: {(scale * 100).toFixed(0)}%</span>
        </div>

        <div
          ref={canvasRef}
          className="relative border border-gray-300 overflow-auto"
          style={{
            width: '100%',
            height: 'calc(100% - 100px)',
            cursor: 'crosshair'
          }}
          onClick={handleCanvasClick}
          onWheel={handleWheel}
        >
          <div style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}>
            {/* 底层：模板预览图 */}
            <img
              src={template.previewImage}
              alt="画布"
              style={{ display: 'block', pointerEvents: 'none' }}
            />

            {/* 叠加层：已填充的素材 */}
            {template.elements.map(element => {
              const materialId = materialMappings.get(element.id);
              if (!materialId) return null;

              const material = availableMaterials.find(m => m.id === materialId);
              if (!material) return null;

              const imgElement = canvasRef.current?.querySelector('img');
              const displayScale = imgElement ? imgElement.clientWidth / template.canvasSize.width : 1;

              return (
                <div
                  key={element.id}
                  className={`absolute ${
                    selectedElementId === element.id
                      ? 'ring-4 ring-blue-500'
                      : 'ring-2 ring-green-500'
                  }`}
                  style={{
                    left: `${element.position.x * displayScale}px`,
                    top: `${element.position.y * displayScale}px`,
                    width: `${(element.cutSize.width * 10) * displayScale}px`,
                    height: `${(element.cutSize.height * 10) * displayScale}px`,
                    transform: element.rotation === 90 ? 'rotate(-90deg)' : 'none',
                  }}
                >
                  <img
                    src={`/api${material.filePath}`}
                    className="w-full h-full object-cover opacity-80"
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button onClick={handleSave}>保存为打印素材</Button>
        </div>
      </div>
    </div>
  );
};
```

---

#### 组件4：`PrintMaterialList.tsx`

```typescript
export const PrintMaterialList = () => {
  const [materials, setMaterials] = useState<PrintMaterialFile[]>([]);

  useEffect(() => {
    loadMaterials();
  }, []);

  const loadMaterials = async () => {
    const list = await api.getPrintMaterials();
    setMaterials(list);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此打印素材？')) return;

    await api.deletePrintMaterial(id);
    loadMaterials();
  };

  return (
    <div>
      <h3 className="font-bold mb-4">打印素材</h3>

      <div className="grid grid-cols-2 gap-4">
        {materials.map(material => (
          <div key={material.id} className="border p-2">
            <img
              src={`/api/print-materials/${material.id}/preview`}
              className="w-full h-32 object-contain mb-2"
            />
            <p className="text-sm font-medium truncate">{material.fileName}</p>
            <p className="text-xs text-gray-500">
              {(material.fileSize / 1024 / 1024).toFixed(2)} MB
            </p>
            <div className="flex gap-1 mt-2">
              <Button
                size="sm"
                onClick={() => window.open(`/api/print-materials/${material.id}/pdf`)}
              >
                下载
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleDelete(material.id)}
              >
                删除
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 六、实施计划

### Phase 1：基础设施（PSD 解析和上传）
- [ ] 创建 `backend/psd_layout_parser.py`
- [ ] 实现 `parse_psd_file()` 函数
- [ ] 实现 `match_layers_to_die_elements()` 函数
- [ ] 实现 `generate_preview_image()` 函数
- [ ] 修改 `backend/layout_template_manager.py`
  - [ ] 新增 `create_from_psd()` 方法
  - [ ] 清空旧格式模板数据
- [ ] 新增 API: `POST /api/layout-templates/upload-psd`
- [ ] 前端：创建 `LayoutTemplateUpload.tsx`
- [ ] 测试 PSD 上传和匹配流程

### Phase 2：预览和展示
- [ ] 前端：创建 `LayoutTemplatePreview.tsx`
- [ ] 修改 `DieMaterialAndLayoutManager.tsx`
  - [ ] 集成 `LayoutTemplateUpload` 组件
  - [ ] 修改模板卡片点击行为
  - [ ] 添加"使用模板"按钮
- [ ] 测试预览界面和跳转逻辑

### Phase 3：排版编辑器
- [ ] 前端：创建 `PrintArrangementEditor.tsx`
  - [ ] 实现画布热区映射
  - [ ] 实现滚轮缩放
  - [ ] 实现素材筛选展示
  - [ ] 实现已填充素材可视化
- [ ] 修改 `App.tsx`
  - [ ] 新增"排版打印" Tab
  - [ ] 实现 Tab 跳转逻辑
- [ ] 测试完整排版流程

### Phase 4：PDF 生成和存储
- [ ] 修改 `backend/print_material_generator.py`
  - [ ] 调整 `generate_print_material()` 函数
  - [ ] 支持旋转绘制
  - [ ] 生成预览图
- [ ] 新增 API:
  - [ ] `POST /api/print-materials/generate`
  - [ ] `GET /api/print-materials`
  - [ ] `GET /api/print-materials/:id/pdf`
  - [ ] `GET /api/print-materials/:id/preview`
  - [ ] `DELETE /api/print-materials/:id`
- [ ] 前端：创建 `PrintMaterialList.tsx`
- [ ] 修改 `DieMaterialAndLayoutManager.tsx` 集成打印素材列表
- [ ] 测试 PDF 生成和下载

---

## 七、注意事项

### 7.1 单位转换统一原则
- **PSD 解析**：像素 → mm（使用 DPI）
- **刀模元素**：cm → mm（统一后比较）
- **PDF 生成**：mm → reportlab 单位（mm * units.mm）
- **前端显示**：mm → px（通过缩放比例）

### 7.2 旋转处理
- **匹配时**：交换宽高进行比较
- **绘制时**：使用 PIL 预旋转图像（避免 reportlab 变换复杂性）
- **前端显示**：CSS `transform: rotate(-90deg)` 或交换宽高

### 7.3 缩放功能
- **实现方式**：CSS `transform: scale()`
- **缩放范围**：0.5x ~ 3x
- **不影响生成**：缩放仅用于预览，实际 PDF 按原始尺寸生成

### 7.4 数据清理
- 在实施前检查 `layout_templates/templates.json`，清空旧格式数据
- 确保所有模板都包含新字段：`canvasSize`, `position`, `rotation`

---

## 八、类型定义

```typescript
// frontend/src/types/index.ts

export interface LayoutTemplate {
  id: string;
  name: string;
  psdFileName: string;
  canvasSize: {
    width: number;   // mm
    height: number;  // mm
  };
  elements: LayoutElement[];
  previewImage: string;
  createdAt: string;
}

export interface LayoutElement {
  id: string;
  elementId: string;
  elementName: string;
  cutSize: {
    width: number;   // cm
    height: number;  // cm
  };
  position: {
    x: number;       // mm
    y: number;       // mm
  };
  rotation: 0 | 90;
  layerIndex: number;
}

export interface PrintMaterialFile {
  id: string;
  fileName: string;
  fileSize: number;
  createdAt: string;
  previewUrl: string;
}
```

---

## 九、API 接口详细定义

```python
# backend/app.py

@app.route('/api/layout-templates/upload-psd', methods=['POST'])
def upload_psd_template():
    """上传 PSD 文件并创建布局模板"""
    if 'psd' not in request.files:
        return jsonify({'error': '未找到 PSD 文件'}), 400

    psd_file = request.files['psd']

    # 保存临时文件
    temp_path = f"/tmp/{uuid.uuid4()}.psd"
    psd_file.save(temp_path)

    try:
        # 创建模板
        template = layout_template_manager.create_from_psd(
            temp_path,
            name=request.form.get('name', os.path.splitext(psd_file.filename)[0])
        )
        return jsonify(template), 200
    except ValueError as e:
        # 匹配失败
        return jsonify({
            'error': e.args[0]['message'],
            'unmatched_layers': e.args[0]['unmatched_layers']
        }), 400
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/print-materials/generate', methods=['POST'])
def generate_print_material():
    """生成打印素材（PDF + 预览图）"""
    data = request.json
    template_id = data['templateId']
    material_mappings = {m['layoutElementId']: m['materialId']
                         for m in data['materialMappings']}

    # 加载模板
    template = layout_template_manager.get_template(template_id)

    # 生成 PDF
    output_dir = 'storage/print_materials'
    os.makedirs(output_dir, exist_ok=True)

    result = print_material_generator.generate_print_material(
        template,
        material_mappings,
        output_dir
    )

    return jsonify({
        'pdfId': result['pdf_id'],
        'fileSize': result['file_size']
    }), 200


@app.route('/api/print-materials', methods=['GET'])
def get_print_materials():
    """获取打印素材列表"""
    materials_dir = 'storage/print_materials'
    files = []

    for filename in os.listdir(materials_dir):
        if filename.endswith('.pdf'):
            pdf_id = filename[:-4]
            pdf_path = os.path.join(materials_dir, filename)
            preview_path = os.path.join(materials_dir, f'{pdf_id}_preview.png')

            files.append({
                'id': pdf_id,
                'fileName': filename,
                'fileSize': os.path.getsize(pdf_path),
                'createdAt': datetime.fromtimestamp(
                    os.path.getctime(pdf_path)
                ).isoformat(),
                'previewUrl': f'/api/print-materials/{pdf_id}/preview'
            })

    return jsonify(files), 200


@app.route('/api/print-materials/<pdf_id>/pdf', methods=['GET'])
def download_print_material_pdf(pdf_id):
    """下载 PDF"""
    pdf_path = f'storage/print_materials/{pdf_id}.pdf'
    return send_file(pdf_path, mimetype='application/pdf',
                     download_name=f'{pdf_id}.pdf')


@app.route('/api/print-materials/<pdf_id>/preview', methods=['GET'])
def get_print_material_preview(pdf_id):
    """获取预览图"""
    preview_path = f'storage/print_materials/{pdf_id}_preview.png'
    return send_file(preview_path, mimetype='image/png')


@app.route('/api/print-materials/<pdf_id>', methods=['DELETE'])
def delete_print_material(pdf_id):
    """删除打印素材"""
    pdf_path = f'storage/print_materials/{pdf_id}.pdf'
    preview_path = f'storage/print_materials/{pdf_id}_preview.png'

    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    if os.path.exists(preview_path):
        os.remove(preview_path)

    return jsonify({'success': True}), 200
```
