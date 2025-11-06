# 打印排版系统前端重构计划

## 概述

将打印排版功能从"素材排版"改为"元素布局设计 + 素材填充"两阶段工作流。

## 核心改动

### 一、PrintLayout.tsx（打印排版页面）

#### 1. 状态管理改动

**新增状态：**
- `mode`: 'design' | 'fill' - 工作模式
- `loadedTemplate`: LayoutTemplate | null - 载入的模版
- `canvasElements`: CanvasElement[] - 画布上的元素（替代原 canvasMaterials）
- `materialAssignments`: Record<layoutElementId, materialId> - 素材分配映射

**移除状态：**
- 原有的 `canvasMaterials` 相关逻辑

**数据结构变化：**
```typescript
// 原来
interface CanvasMaterial {
  id, materialId, x, y, rotation, scale, width, height, imageUrl, imageObj
}

// 现在
interface CanvasElement {
  id,           // 画布元素ID
  elementId,    // 刀模元素ID
  elementName,
  x, y,         // mm
  rotation,     // 0/90/180/270
  width, height // mm
}
```

#### 2. 左侧栏改动

**design 模式：**
- 显示刀模元素列表（从 `/api/die-elements` 获取）
- 仅显示：元素名称 + 尺寸（例：5×5cm）
- 无预览图
- 宽度：col-span-2
- 点击元素 → 添加到画布

**fill 模式：**
- 显示模版用到的刀模元素
- 按元素ID分组
- 每组显示该元素的所有可用素材（从 `/api/die-materials?elementId=xxx` 获取）
- 点击素材 → 打开素材选择对话框

#### 3. 画布区域改动

**design 模式：**
- 渲染：蓝色1px边框矩形 + 元素名称（居中显示）
- 使用 Konva Rect + Text 替代 Image
- 保持拖动、旋转、吸附、边界限制功能

**fill 模式：**
- 未分配素材：蓝色边框 + 元素名称
- 已分配素材：显示素材图片（使用 Konva Image）
- 点击元素 → 打开素材选择对话框

#### 4. 顶部操作改动

**design 模式：**
- "保存为模版" 按钮 → 打开 TemplateNameDialog
- 移除"保存并下载PDF"按钮

**fill 模式：**
- "返回设计模式" 按钮
- "生成打印PDF" 按钮（仅当所有元素都分配素材后可用）
- 点击生成 → 调用 `/api/print-materials` → 返回素材管理页面

#### 5. 模版载入逻辑

**从素材管理页跳转过来：**
- 接收 templateId 参数（通过路由或状态管理）
- 清空画布
- 载入模版数据
- 设置 mode = 'fill'
- 初始化 canvasElements（从模版的 elements 生成）
- 检查元素有效性（去除已删除的刀模元素）

---

### 二、DieMaterialAndLayoutManager.tsx（素材与排版管理）

#### 1. 布局改动

**从 2列 改为 3列：**
```
grid-cols-3 gap-6

第1列：刀模素材（保持原有）
第2列：可用模版（新增）
第3列：打印素材（新增）
```

#### 2. 第1列 - 刀模素材

**保持现有功能：**
- 分组显示刀模素材
- 预览、下载、删除
- 选择功能（保留但不再使用"用于排版"按钮）

#### 3. 第2列 - 可用模版

**数据来源：** `/api/layout-templates`

**卡片显示：**
- 预览图（Base64 image，带分割线）
- 模版名称
- 纸张信息（A4 横向）
- 创建时间

**点击卡片：**
- 打开 TemplateDetailDialog

**操作按钮（在详情对话框中）：**
- "使用排版" → 跳转到 PrintLayout（fill模式）
- "删除" → 调用 `/api/layout-templates/{id}` DELETE

#### 4. 第3列 - 打印素材

**数据来源：** `/api/print-materials`

**卡片显示：**
- 预览图（Base64 image，完整拼接后的PDF预览）
- 生成时间

**点击卡片：**
- 打开 PrintMaterialDetailDialog

**操作按钮（在详情对话框中）：**
- "下载PDF" → 下载 `/api/print-materials/{id}/pdf`
- "查看详情" → 显示素材映射关系
- "删除" → 调用 `/api/print-materials/{id}` DELETE

---

### 三、新增组件

#### 1. TemplateNameDialog.tsx

**用途：** 保存模版时输入名称

**UI：**
- 对话框标题："保存布局模版"
- 输入框：模版名称（必填）
- 确认/取消按钮

**逻辑：**
- 接收 props: isOpen, onClose, onSave
- onSave(name: string) → 父组件处理保存逻辑
- 调用 `/api/layout-templates` POST

---

#### 2. MaterialSelectionDialog.tsx

**用途：** fill 模式下为元素选择素材

**UI：**
- 对话框标题："选择素材 - {elementName}"
- 显示该元素的所有可用素材（网格布局）
- 三个选项（单选）：
  - □ 仅填入当前元素
  - □ 画布上所有同元素均填入该素材
  - □ 画布上尚未选择的同元素均填入该素材
- 确认/取消按钮

**逻辑：**
- 接收 props:
  - isOpen
  - elementId
  - elementName
  - currentLayoutElementId
  - onClose
  - onSelect(materialId, option)
- 从 `/api/die-materials?elementId={elementId}` 获取素材列表
- onSelect → 父组件更新 materialAssignments

---

#### 3. TemplateDetailDialog.tsx

**用途：** 查看模版详情

**UI：**
- 对话框标题："模版详情"
- 大预览图
- 模版信息：
  - 名称
  - 纸张大小
  - 方向
  - 创建时间
- 元素统计列表（表格）：
  - 元素名称
  - 尺寸
  - 数量（同一元素在画布上出现的次数）
- 操作按钮：
  - "使用排版" → 跳转到 PrintLayout（fill模式）
  - "删除"
  - "关闭"

**逻辑：**
- 接收 props: isOpen, template, onClose, onUseTemplate, onDelete
- 统计每个元素的出现次数

---

#### 4. PrintMaterialDetailDialog.tsx

**用途：** 查看打印素材详情

**UI：**
- 对话框标题："打印素材详情"
- 大预览图
- PDF信息：
  - 名称
  - 使用的模版
  - 文件大小
  - 创建时间
- 素材映射表格：
  - 元素名称
  - 使用的素材文件名
  - 数量（该素材使用次数）
- 操作按钮：
  - "下载PDF"
  - "删除"
  - "关闭"

**逻辑：**
- 接收 props: isOpen, printMaterial, onClose, onDownload, onDelete
- 统计每个素材的使用次数

---

## 实施步骤

1. ✅ 后端API已完成
2. ✅ 前端类型定义已完成
3. ✅ API服务已完成
4. ⏳ 创建4个对话框组件
5. ⏳ 修改 PrintLayout.tsx
6. ⏳ 修改 DieMaterialAndLayoutManager.tsx
7. ⏳ 测试完整工作流

---

## 关键技术点

### 1. 画布元素渲染（design模式）

使用 Konva Rect + Text 替代 Image：
```typescript
<Rect
  x={element.x}
  y={element.y}
  width={element.width}
  height={element.height}
  stroke="blue"
  strokeWidth={1}
  rotation={element.rotation}
  draggable
/>
<Text
  x={element.x}
  y={element.y + element.height/2}
  text={element.elementName}
  fill="blue"
  fontSize={10}
/>
```

### 2. 预览图生成（后端已实现）

- 布局模版预览：后端使用 PIL 绘制分割线 + 元素名称
- 打印素材预览：后端使用 PIL 拼接素材图片

### 3. 素材映射逻辑（fill模式）

```typescript
// 记录分配
materialAssignments = {
  'layout-element-1': 'material-123',
  'layout-element-2': 'material-456',
  // ...
}

// 检查是否全部分配
const allAssigned = canvasElements.every(
  el => materialAssignments[el.id]
);

// 生成PDF时提交
const mappings = canvasElements.map(el => ({
  layoutElementId: el.id,
  materialId: materialAssignments[el.id],
  elementId: el.elementId
}));
```

### 4. 路由/状态管理（跳转逻辑）

使用 React state 传递 templateId：
- 在 DieMaterialAndLayoutManager 中点击"使用排版"
- 设置 App 级别的 state: `loadTemplateId`
- 切换到 PrintLayout tab
- PrintLayout 检测到 loadTemplateId，载入模版并切换到 fill 模式

---

## 注意事项

1. **元素有效性检查**：载入模版时，检查所有元素是否仍存在，去除已删除的元素
2. **尺寸单位统一**：cutSize 使用 cm，画布坐标使用 mm
3. **预览图缓存**：预览图为 Base64，已包含在 JSON 响应中，无需额外请求
4. **PDF下载**：使用 `<a>` 标签 + download 属性，或 `window.open()`

---

## 文件清单

**新增文件：**
- `frontend/src/components/TemplateNameDialog.tsx`
- `frontend/src/components/MaterialSelectionDialog.tsx`
- `frontend/src/components/TemplateDetailDialog.tsx`
- `frontend/src/components/PrintMaterialDetailDialog.tsx`

**修改文件：**
- `frontend/src/components/PrintLayout.tsx` - 大改
- `frontend/src/components/DieMaterialAndLayoutManager.tsx` - 大改
- `frontend/src/App.tsx` - 添加状态管理和跳转逻辑

**已完成文件：**
- `backend/layout_template_manager.py`
- `backend/print_material_generator.py`
- `backend/app.py`
- `frontend/src/types/index.ts`
- `frontend/src/services/api.ts`
