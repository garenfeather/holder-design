# 🎯 Holder Design · PSD 模板管理与生成器

优雅、简洁、现代化的 PSD 模板管理工具：上传模板、生成 inside（restored）与多种 stroke 版本、参考图预览、按所选“裁切模板”（原始/指定 stroke）进行生成，提供结果管理、下载与清理能力。

## 📦 关键特性

- 模板入库：校验必需图层（view、part1~4），生成模板预览与编辑参考图，产出 `restored.psd`。
- 多 stroke 版本：可在上传时配置 `strokeWidths`（如 2/5/8），生成对应 inside PSD 与二阶段透明参考图。
- 统一参考图渲染：原参考图与 stroke 参考图复用一致的渲染逻辑（仅输入 PSD 不同）。
- 裁切模板选择：生成时可选“原始 inside”或某个已存在的 stroke inside；仅在点击生成时应用。
- 结果标注与命名：结果 `result_id` 及文件名追加 `_stroke_{w}px` 后缀；详情返回 `usedStrokeWidth`。
- 结果管理：列表/详情/下载/删除/批量清理，详情预览样式与“生成结果预览”一致（灰底 + 自适应）。
- 自动清理：生成过程临时文件会被清理；提供 `clean_storage.sh` 做开发期一键清空。

## 🏗️ 项目结构

```
holder-design/
├── backend/
│   ├── app.py                 # Flask 入口与路由
│   ├── processor_core.py      # 核心编排（校验/入库/生成/索引）
│   ├── png_stroke_processor.py# PNG描边处理（SciPy/PIL）
│   ├── psd_replacer.py        # 按图层形状（alpha）进行裁切替换
│   ├── psd_transformer.py     # 最终变换（扩展画布、翻转/移动）
│   ├── psd_resizer.py         # PSD 尺寸调整
│   ├── transformer_inside.py  # 逆展开（生成 restored.psd）
│   └── ...
├── frontend/
│   └── src/...                # React 前端（npm start 开发）
├── clean_storage.sh           # 一键清空 storage（开发期）
└── storage/
    ├── templates/            # 模板与索引 templates.json（数组）
    ├── inside/               # {tpl}_restored.psd、{tpl}_stroke_{w}px.psd
    ├── previews/             # 模板预览图
    ├── references/           # 原/各 stroke 的透明参考图
    └── results/              # 结果：downloads/、previews/、results_index.json
```

> 说明：`results_index.json` 为对象结构，包含 `results` 字典；系统对旧格式 `[]` 做了兼容并自动规范化。

## 🚀 启动

后端（默认 8012）：
```bash
cd backend
python3 app.py --debug
```

前端（默认 8001）：
```bash
cd frontend
npm install
npm start
```

便捷脚本：`./restart_services.sh` 同时启动前后端；`./clean_storage.sh` 清空 storage（开发期使用）。

## 🔧 依赖

后端：
```bash
pip install flask flask-cors psd-tools Pillow numpy scipy
```
> 提示：`scipy` 可选但推荐，用于更平滑的描边算法；缺失时会降级走 PIL 路径。

前端：
```bash
cd frontend && npm install
```

## 🔌 API（要点）

- 健康检查：`GET /api/health`
- 模板管理：
  - `POST /api/upload`：`template`(PSD)＋可选 `strokeWidths=[2,5,8]`，入库并生成 restored / 预览 / 参考图 / 多 stroke inside 与参考图
  - `GET /api/templates`、`GET /api/templates/{id}/preview`、`GET /api/templates/{id}/reference`
  - `GET /api/templates/{id}/stroke/{w}/reference`：获取指定宽度的透明参考图（已存在的 stroke）
  - `POST /api/templates/{id}/delete`
- 生成：
  - `POST /api/generate`
    - 表单字段：
      - `templateId`(必填)、`image`(必填)
      - `forceResize`(可选，bool)
      - `componentId`(可选)
      - `strokeWidth`(可选，number；不传表示“原始 inside”)
    - 约束：仅允许选择模板已配置并已存在的 stroke 版本；缺失时返回错误，不自动生成新 stroke。
    - 返回：包含 `resultId`、`usedStrokeWidth`、`previewPath` 等。
- 结果管理：
  - `GET /api/results` 列表（时间倒序）
  - `GET /api/results/{id}/info` 详情（含 `usedStrokeWidth`）
  - `GET /api/results/{id}/preview`、`GET /api/results/{id}/download`
  - `DELETE /api/results/{id}/delete`
  - `POST /api/results/cleanup`（`keepRecent`、`olderThanDays`、`dryRun`）
- 部件：上传/获取/重命名/删除（见 `backend/app.py` 对应路由）。

## 🔁 生成流程（更新版）

1. 模板上传：校验图层、保存、生成模板预览、生成 `restored.psd`。
2. （可选）多 stroke：按 `strokeWidths` 生成 `{tpl}_stroke_{w}px.psd` 与对应透明参考图。
3. 前端选择：在“裁切模板选择”区域选择“原始”或某个 stroke（仅展示已存在项）；叠加参考图仅用于视觉对比，点击“生成”时才应用。
4. 生成时：
   - 未选 stroke → 使用 `restored.psd`；已选 → 使用对应 `stroke` inside PSD。
   - 进行尺寸对齐 → 按图层形状裁切替换 → 最终变换 → 生成 `final.psd` 与预览。
5. 命名与索引：
   - `result_id` 追加 `_stroke_{w}px`（若选择了 stroke）。
   - 详情返回 `usedStrokeWidth`；索引记录 `used_stroke_width`。

## 🖼️ 前端交互（要点）

- 裁切模板选择：
  - 标题“裁切模板选择”；按钮文案“选择模板”（原“对比”功能位，控制叠加可视化）。
  - 下拉：`原始` + `strokeConfig` 中已有的宽度；不生成新 stroke。
  - 预览叠加：与选择联动（原始/Stroke Npx）。
- 生成结果详情：
  - 预览样式与生成预览一致（灰底容器 + 图片自适应）。
  - 基本信息位于预览下方，显示“使用模板：原始 / Stroke Npx”。
- 下载命名：文件名自动追加 `_stroke_{w}px` 后缀（若选择了 stroke）。

## 🗂️ 索引结构（概要）

- 模板索引（`storage/templates/templates.json`）：数组，每条记录包含 `id/name/savedFileName/restoredFileName/previewImage/referenceImage/strokeVersions/strokeReferences/strokeConfig/...`。
- 结果索引（`storage/results/results_index.json`）：
```json
{
  "version": "1.0",
  "last_updated": "...",
  "results": {
    "result_..._stroke_5px": {
      "id": "result_..._stroke_5px",
      "template_id": "tpl_...",
      "template_name": "...",
      "created_at": "...",
      "final_psd_size": 123456,
      "used_stroke_width": 5
    }
  }
}
```
> 兼容：若文件为 `[]`，系统会在读取时自动规范化为上面的对象结构。

## 🧹 清理与中间文件

- 生成流程使用临时文件/目录，结束后会清理，只保留最终 `final.psd` 与对应预览图。
- `clean_storage.sh`：清空 `storage` 下的文件（开发期使用）。

## 📝 常见问题

- 选择了某个 stroke，但提示“所选stroke版本文件不存在”？
  - 说明该 PSD 文件被手工清理或未生成；系统不会自动补生成，请重新上传模板或恢复文件。
- 参考图与 stroke 参考图为什么看起来一致？
  - 它们使用相同的渲染逻辑，仅输入 PSD 不同（原始 inside vs 对应 stroke inside）。

## 📄 许可证

MIT License

—— 让 PSD 模板管理与生成更优雅高效。
