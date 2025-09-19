# Inside 多描边（stroke）修订方案（对齐现有代码）

## 背景与目标
- 在不推翻现有处理链路的前提下，引入“多描边版本”的 inside 能力：可配置若干描边宽度，生成对应的 inside 变体 PSD 与预览，用于编辑时对比与生成时选择。
- 保持现有模块职责不变：InsideTransformer 继续处理 PSD 级变换；PSDCropper 继续执行按 view 裁剪；索引仍以 `templates.json` 为主来源。

## 现状与差异
- 现有流程（已实现）：
  - 上传模板 → 验证 → 生成预览（part 合成 + 50% 灰）→ InsideTransformer 生成 `{id}_restored.psd`（inside+按 view 裁剪）→ 基于 restored 生成编辑参考图（references）。
- 原技术方案（描边inside.md）与现状不完全对齐：
  - 文档按“PNG 抽取 → inside 变换 → 重组 PSD”的 PNG 流程组织，而当前 inside 变换是 PSD 级完成，随后再裁剪。
  - 文档计划对“所有 PNG”做 inside 变换，易误伤 view/其他层；并未明确裁剪时机与对齐规则。

## 修订后总体流程（与现有代码对齐）
1. 继续生成 `{id}_restored.psd`：保持 InsideTransformer + PSDCropper 的现有逻辑与路径（`storage/inside/{id}_restored.psd`）。
2. 基于 restored.psd 抽取 part 图层为全画布 PNG（使用现有 PSDScaler.extract_layers_from_psd；其已将图层按 left/top 粘贴到全尺寸画布，坐标对齐天然正确）。
3. 对每个配置的描边宽度 w：
   - 对每个 part PNG 生成“描边图层 PNG（仅描边）”。推荐直接复用 `scripts/png_edge_stroke.py` 的内部逻辑，产出纯描边 RGBA（不包含原图），而非合成后的“原图+描边”。
   - 将“描边图层 PNG（底）+ 原 part PNG（顶）”重组为变体 PSD，或将描边图层插入 restored.psd 的相应 part 层之下（建议新建 PSD，以避免破坏 restored.psd）。
   - 生成半透明预览图（50%），尺寸/偏移与 restored 参考图一致，便于叠加对比。
4. 更新模板索引（templates.json），将“多描边变体”作为模板记录的子项进行维护（见下）。

## 文件命名与存储
- 统一以模板 id 命名，避免 name 冲突，延续现有风格：
  - restored：`storage/inside/{id}_restored.psd`
  - 变体 PSD：`storage/inside/{id}_inside_stroke_{w}px.psd`
  - 变体预览（半透明，用于叠加参考）：`storage/references/{id}_stroke_{w}px_reference.png`
- 临时文件：使用 `tempfile.TemporaryDirectory()`；流程末尾清理。

## 模板索引结构调整（templates.json）
在每个模板记录内新增字段（不改动现有字段）：
```
insideVariants: [
  {
    id: string,                // 变体ID，例如 "stroke_5px"
    width: number,             // 描边宽度（px）
    psdFile: string,           // 相对路径，例如 inside/{id}_inside_stroke_5px.psd
    referenceImage: string,    // 相对路径，例如 references/{id}_stroke_5px_reference.png
    createdAt: ISOString
  }, ...
]
```
可选：`defaultStrokeWidths: number[]`（保存常用配置，便于复用）。

删除模板时，需一并清理 `insideVariants` 对应的 PSD 与 reference 图（现状删除代码仅处理 `insideFileName`，请统一改为 `restoredFileName` + `insideVariants` 清理）。

## 后端 API 设计（与现有风格一致）
- 生成变体（批量）：
  - `POST /api/templates/{template_id}/inside/variants`
  - body：`{ widths: number[], color?: string|rgba, alpha?: number, smooth?: number }`
  - 返回：`{ success, data: { variants: InsideVariant[] } }`
- 列出变体：
  - `GET /api/templates/{template_id}/inside/variants`
  - 返回：`{ success, data: InsideVariant[] }`
- 删除单个变体：
  - `DELETE /api/templates/{template_id}/inside/variants/{variant_id}`
  - 作用：删除变体 PSD + reference + 索引项
- 取变体预览（半透明参考图）：
  - `GET /api/templates/{template_id}/inside/variants/{variant_id}/preview`
  - 直接 `send_file` 对应 reference 图
- 下载变体 PSD：
  - `GET /api/templates/{template_id}/inside/variants/{variant_id}/psd`

生成最终 PSD 接口扩展：
- `POST /api/generate` 保持向后兼容，新增可选参数：
  - `insideVariantId?: string`（优先）或 `strokeWidth?: number`
  - 选择规则：优先 `insideVariantId`；若仅 `strokeWidth`，匹配已有变体；均未提供则使用 `{id}_restored.psd`。

## 处理逻辑建议（processor_core）
- 新增：`generate_inside_variants(template_id, widths, color?, alpha?, smooth?)`：
  1) 读取 `{id}_restored.psd`；
  2) 使用 `PSDScaler.extract_layers_from_psd` 导出全画布 PNG（仅取 part1–4）；
  3) 对每个 `w`：
     - 对 part PNG 计算“描边蒙版”并着色为 RGBA（推荐直接生成“描边层 PNG”，不包含原图）。
     - 重组变体 PSD（顺序：view→partX_stroke_w→partX）或维持现有层顺序，在每个 part 下方插入 `*_stroke_w` 层；
     - 生成半透明参考图（借鉴 `_generate_reference_image`）：仅合成描边层并降透明度，确保与编辑叠加时像素对齐；
     - 写入 `insideVariants` 索引；
  4) 清理临时目录。
- 索引读写：复用 `templates.json` 的读写函数，避免新增散落的 metadata 文件。
- 删除模板：扩展现有 `delete_template`，删除 `restoredFileName`、全部 `insideVariants.*` 文件，并写回索引。

## 参数与校验
- `widths`：建议 1–50 px，去重并排序；允许空数组（跳过生成）。
- 颜色：默认白色 `rgba(255,255,255,255)`；支持 `#RRGGBB` 与 `R,G,B,A`。
- smooth（平滑因子）：默认 1.0；向下兼容 `png_edge_stroke.py` 的参数。
- 失败处理：单个变体失败不影响其他，记录 `failed: [variantId...]` 并返回。

## 依赖与一致性
- `scripts/png_edge_stroke.py` 需要 NumPy/Scipy 才能走主路径；若无则走 fallback，效果略有差异。建议部署侧安装 SciPy，或在后端选择性启用 fallback 并在响应中标注 `algorithm: 'scipy' | 'fallback'`。

## 预览/参考的一致性
- 生成的 reference（半透明）尺寸、裁剪、坐标与 `{id}_restored.psd` 保持一致；前端叠加无需位移计算。
- 变体 preview 的获取通过新端点完成，不影响现有 `GET /api/templates/{id}/reference`。

## 前端改动点（概述）
- 上传或模板详情页：新增“描边配置”输入（单/多），调用批量生成端点；展示已有变体列表。
- 编辑界面对比：新增变体选择，下发并叠加半透明 reference 图；可与现有“参考图”切换。
- 生成流程：可选传 `insideVariantId`。

## 兼容性与迁移
- 旧模板 `insideVariants` 为空；前端保持回退到 `restored.psd`。
- 删除模板时同步删除全部变体文件；修复现有 `insideFileName` 清理遗漏（统一为 `restoredFileName`）。

## 性能与清理
- 中间产物一律使用 `TemporaryDirectory` 并在成功/失败后清理。
- 可选缓存：对相同 `width` 的变体重复请求直接复用（查索引存在即跳过重算）。
- 可提供后端维护端点：按模板移除全部变体 `DELETE /api/templates/{id}/inside/variants`（可选）。

## 风险与边界情况
- 画布边缘描边被裁切：需在 stroke 生成阶段留意边缘，或在重组时扩大临时画布再裁剪回视图尺寸（额外成本）。
- part 接缝叠加：相邻 part 的描边可能在接缝处叠加变粗；如需规避，可在描边层合成时对接缝区域作一次“min”合成或限幅处理（后续迭代）。

## 实施清单（分阶段）
- 后端：
  1) 修复删除逻辑：统一删除 `restoredFileName` 与 `insideVariants`（模板删除）。
  2) 新增 `generate_inside_variants(...)` 核心逻辑（processor_core）。
  3) 新增 5 个 API 端点（生成/列出/删除/预览/下载）。
  4) `/api/generate` 支持 `insideVariantId`（或 `strokeWidth`）。
- 前端：
  1) 类型扩展：`InsideVariant`。
  2) 新增描边配置 UI 与变体列表。
  3) 编辑视图叠加半透明 reference，支持切换与生成时选择。
- 文档：更新 README + 开发说明；记录依赖、参数与示例。

---
以上方案最小化改动面，最大限度复用现有 Inside 与索引机制，保证坐标/尺寸/裁剪一致性，并提供清晰的 API 与清理策略，便于逐步落地。
