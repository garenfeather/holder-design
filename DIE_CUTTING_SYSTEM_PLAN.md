# 刀模系统实现方案

## 一、整体架构调整

### 前端UI结构重组
- **当前**：单层Tab结构（模板箱子 | 生成素材管理）
- **改为**：双层Tab结构
  - **Tab组1**：现有功能（模板箱子 | 生成素材管理）
  - **Tab组2**：刀模系统（刀模元素管理 | 生成刀模素材管理 | 打印排版）

---

## 二、功能模块设计

### 1. 刀模元素管理

#### 前端组件
- **DieElementList.tsx** - 元素列表管理
  - 展示元素卡片（名称、裁切尺寸、参考尺寸、形状预览）
  - 创建元素表单（输入两个尺寸，单位cm）
  - 编辑、删除功能

- **DieElementEditor.tsx** - 元素素材生成
  - 复用 UseModal.tsx 核心裁切逻辑
  - 双尺寸显示：
    - 裁切框：实际切割线，红色实线
    - 参考框：设计参考线，半透明蓝色虚线
  - 图片上传、缩放、旋转、裁切
  - 保存为PNG

#### 数据模型
```typescript
DieElement {
  id: string
  name: string
  cutSize: {width: number, height: number}      // cm
  referenceSize: {width: number, height: number} // cm
  createdAt: string
  updatedAt: string
}
```

#### 后端API
- `GET /api/die-elements` - 获取元素列表
- `POST /api/die-elements` - 创建元素
- `PUT /api/die-elements/<id>` - 更新元素
- `DELETE /api/die-elements/<id>` - 删除元素
- `POST /api/die-elements/<id>/generate` - 生成刀模素材

#### 存储结构
```
storage/die_elements/
├── elements.json
└── materials/
    └── element_id/
        └── *.png
```

---

### 2. 生成刀模素材管理

#### 前端组件
- **DieMaterialManager.tsx** - 素材管理
  - 按刀模元素分组展示
  - 素材缩略图预览
  - 操作：预览、下载、删除、选择（用于排版）
  - 搜索和筛选
  - 批量选择

#### 数据模型
```typescript
DieMaterial {
  id: string
  elementId: string
  fileName: string
  filePath: string
  cutSize: {width: number, height: number}
  referenceSize: {width: number, height: number}
  createdAt: string
}
```

#### 后端API
- `GET /api/die-materials` - 获取所有素材（按元素分组）
- `GET /api/die-materials/element/<element_id>` - 获取某元素素材
- `DELETE /api/die-materials/<id>` - 删除素材
- `GET /api/die-materials/<id>/download` - 下载素材

---

### 3. 打印排版

#### 前端组件
- **PrintLayout.tsx** - 主排版组件
  - 纸张选择器（A3/A4）
  - 双列布局：
    - 左列：素材选择区
    - 右列：排版画布

- **CanvasEditor.tsx** - 画布编辑器（使用 Konva.js）
  - 拖拽素材到画布
  - 移动、旋转素材
  - 吸附功能：
    - 素材边缘互相吸附
    - 边缘与安全区吸附
    - 阈值：5px
  - 选中/删除素材

#### 快捷排版功能
1. **水平复制**
   - 选中已放置素材
   - 自动计算当前行可容纳最大数量
   - 沿水平线等间距复制

2. **单一自动排版**
   - 选择一个素材
   - 计算安全区内最大数量（行×列）
   - 自动网格排列

#### 数据模型
```typescript
LayoutProject {
  id: string
  name: string
  paperSize: 'A3' | 'A4'
  materials: Array<{
    materialId: string
    x: number  // mm
    y: number  // mm
    rotation: number
    scale: number
  }>
  createdAt: string
}
```

#### 后端API
- `POST /api/layout/save` - 保存排版布局
- `GET /api/layout/<id>` - 获取排版布局
- `POST /api/layout/generate-pdf` - 生成PDF

#### PDF生成（后端 reportlab）
- 纸张尺寸：A3 (297×420mm) / A4 (210×297mm)
- 出血线：5mm不可排版
- 300DPI渲染
- 计算公式：`px = mm / 25.4 * 300`

---

## 三、技术要点

### 吸附算法
1. 监听拖拽位置
2. 计算与其他素材/边界的距离
3. 距离 < 5px 触发吸附
4. 显示临时辅助线

### 尺寸转换
- 输入/显示：厘米（cm）
- 存储：毫米（mm）
- PDF渲染：像素（300DPI）
- 转换：1cm = 10mm，1mm ≈ 11.81px@300DPI

### 参考尺寸预览
- 双层Canvas/SVG
- 底层：半透明参考框（蓝色，opacity: 0.3）
- 上层：裁切框（红色，opacity: 1.0）

---

## 四、开发步骤

### 阶段1：基础框架
1. App.tsx 重构为双层Tab
2. 创建三个新组件框架
3. 后端基础API和数据模型

### 阶段2：刀模元素管理
1. 元素列表CRUD
2. 复用UseModal裁切逻辑，添加双尺寸支持
3. PNG保存

### 阶段3：素材管理
1. 按元素分组展示
2. 基础操作（预览、删除）
3. 选择功能

### 阶段4：排版画布
1. Konva.js画布搭建
2. 拖拽功能
3. 吸附算法
4. 快捷排版

### 阶段5：PDF生成
1. 后端PDF生成逻辑
2. 尺寸计算和转换
3. 前后端联调

### 阶段6：优化和测试
1. 性能优化
2. 边界测试
3. 用户体验优化

---

## 五、技术难点

1. **双尺寸裁切**：准确叠加显示两个尺寸框
2. **吸附算法精度**：平衡灵敏度和用户体验
3. **PDF尺寸精度**：cm到px转换精确度
4. **大量素材性能**：画布渲染性能优化
5. **快捷排版算法**：最优排列计算

---

## 六、关键文件参考

### 复用现有代码
- `frontend/src/components/UseModal.tsx` - 裁切逻辑
- `frontend/src/services/api.ts` - API服务层
- `backend/app.py` - API路由定义
- `backend/processor_core.py` - 文件处理逻辑
