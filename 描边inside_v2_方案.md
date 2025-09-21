# 描边 inside · v2 技术方案（中心锚点扩画布 + 裁切外扩）

## 一、目标与范围
- 目标：
  - 生成 stroke 版本前，以“中心锚点”将画布四面各外扩 w 像素，再进行描边，避免描边被画布边缘截断。
  - 用户裁剪阶段，若选择了 stroke，则以裁剪中心为基准四面各外扩 w 像素，确保与扩展画布的 stroke inside 完全匹配。
- 范围：仅对 stroke 版本与生成前裁剪交互进行增强；“原始 inside（restored.psd）”的既有流程与体验保持不变。

## 二、术语与约束
- 原始 inside：upload 后产生的 `restored.psd`（不扩展画布）。
- stroke inside：`{tpl}_stroke_{w}px.psd`（v2 中画布尺寸 = 原始尺寸 + 2w，中心锚点扩展）。
- stroke 宽度单位：PSD 像素。
- 仅能选择已存在的 stroke 版本（不在生成阶段临时新建）。

## 三、后端改造
### 3.1 生成 stroke 版本（_generate_single_stroke_version）
- 在开始处理之前，对源 inside PSD 执行“中心锚点扩画布”：
  - 新画布尺寸：`W' = W + 2w`，`H' = H + 2w`。
  - 以中心为锚，内容保持居中不动；不做二次“手动整体偏移”。
- 按现有流程提取 PNG → 对 part 图层执行描边（SciPy/PIL 路径）→ 重组为 PSD，输出 `{tpl}_stroke_{w}px.psd`（使用扩展后的画布尺寸）。
- stroke 参考图：基于“扩展后”的 stroke inside 渲染，PNG 尺寸与 stroke inside 一致。
- 元数据（可选增强）：在模板记录中新增 `strokeMeta[w] = { width, height }`，便于前端按实尺寸切换容器比例（如缺省，前端也可用 view 尺寸 + 2w 估算）。

### 3.2 生成流程（generate_final_psd）
- 入参保持不变：`strokeWidth`（可选）。
- 选择逻辑：
  - 空/未选 → 使用原始 inside（restored.psd）。
  - 选中 w → 使用“扩展画布”的 stroke inside `{tpl}_stroke_{w}px.psd`。
- 其他步骤（尺寸对齐、替换、最终变换、部件叠加）保持一致。
- 结果标注与命名：继续沿用 `_stroke_{w}px` 后缀与 `used_stroke_width` 索引字段。

## 四、前端改造
### 4.1 裁切阶段（UseModal）
- 当选择了 stroke w：
  - 以当前裁剪中心为基准，将裁剪矩形四面各外扩 w 像素；超出原图时 clamp 边界（不引入空白）。
  - 导出（上传）图片的像素范围因此增大，匹配“扩展画布”的 stroke inside，避免描边被截断。
- 未选择 stroke：维持现有裁切行为。

### 4.2 预览容器与叠加
- 预览容器比例：
  - 选择 stroke → 切换为 `(view.width + 2w) : (view.height + 2w)`（或用 `strokeMeta[w].width/height`）。
  - 选择原始 → 维持现有比例 `view.width : view.height`。
- 叠加参考图：与选择联动（原始 / Stroke Npx），展示尺寸与容器一致，实现像素对齐的所见即所得。

### 4.3 生成请求
- 继续向 `/api/generate` 传递 `strokeWidth`；不新增额外参数。
- 下载命名与结果详情标注保持不变（含 `_stroke_{w}px` 与“使用模板：原始 / Stroke Npx”）。

## 五、API 与数据
- 生成接口：`POST /api/generate`，参数与语义保持不变（`strokeWidth` 选择 stroke inside）。
- 参考图：`GET /api/templates/{id}/stroke/{w}/reference` 返回“扩展画布尺寸”的 PNG。
- 模板元数据（可选）：`strokeMeta[w] = { width, height }`，便于前端容器按实尺寸展示。

## 六、兼容与迁移
- 旧 stroke 版本（未扩展画布）：可标记为 legacy；如需一致体验，支持“重新生成 stroke 版本（v2）”。
- 原始 inside：完全保持不变。

## 七、校验与边界
- 选择 stroke=5px：
  - 参考图尺寸较原始增大（宽高各 +10px）。
  - 裁切选区外扩，对齐扩展画布；生成后描边不被截断。
  - 结果 ID/下载名包含 `_stroke_5px`，详情显示“Stroke 5px”。
- 选择原始：行为与当前一致。

## 八、风险与对策
- 比例错位：通过 `strokeMeta` 或严格按 view+2w 切换容器比例，确保前后端一致。
- 体积增加：画布外扩会带来 PSD/PNG 尺寸小幅增加；限制最大 w（如 10px），并复用已生成版本。
- 缺失文件：坚持“仅可选已存在版本”的策略；如文件被清理，提示恢复或重新上传模板生成。

## 九、落地步骤
1) 后端：在 `_generate_single_stroke_version` 增加“中心锚点扩画布”步骤；参考图渲染基于扩展画布；（可选）返回 `strokeMeta`。
2) 前端：裁切外扩逻辑、预览容器比例切换与叠加对齐；生成仍传 `strokeWidth`。
3) 验收：覆盖原始与多个 w（2/5/8）路径，检查预览、裁切边缘、命名与详情标注；对 legacy 版本做提示或再生成。

> 备注：本方案在分支 `extra_stroke` 实施，不影响现有主线功能与用户体验。

