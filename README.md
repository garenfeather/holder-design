# 🎯 PSD Template Processor

现代化PSD模板图片处理工具 - 简洁、高效、专业

## 📋 项目简介

一个基于 Flask 的后端服务与前端页面的工具项目：根据PSD模板中的 `part1-4` 图层对用户上传的图片进行智能裁切与变换，生成包装展开图。支持模板入库、预览/参考图生成、尺寸对齐、最终结果预览与下载。

## 🏗️ 项目结构（实际）

```
psd-template-processor/
├── backend/                      # 后端服务 (Flask)
│   ├── app.py                   # Flask 入口与路由
│   ├── processor_core.py        # 核心编排：校验/存储/生成
│   ├── integrated_processor.py  # 一次性处理器 (process 接口使用)
│   ├── psd_replacer.py          # 按图层形状裁切替换
│   ├── psd_transformer.py       # 画布扩展/翻转/移动（最终变换）
│   ├── psd_resizer.py           # PSD尺寸调整(二进制头+边界)
│   ├── transformer_inside.py    # 逆展开(向内)变换，生成 b.psd
│   └── transformer_outside.py   # 向外变换（备用）
├── frontend/                     # 前端应用（可选）
│   └── package.json 等          # 使用 npm start 本地开发
├── scripts/                      # 独立脚本（与 backend 功能呼应）
│   ├── integrated_processor.py
│   ├── psd_replacer.py
│   ├── psd_resizer_v2.py / full_scale.py
│   ├── transform_to_inside.py
│   └── transform_to_outside.py
└── storage/                      # 持久化存储
    ├── templates/               # 模板源文件与索引 templates.json
    ├── expanded/                # 逆展开 b.psd（{tplId}_restored.psd）
    ├── previews/                # 模板预览图（{tplId}_preview.png）
    ├── references/              # 模板参考图（{tplId}_reference.png）
    └── temp/                    # 生成过程产物（result/final/preview）
```

## 🚀 启动与访问

### 后端服务
```bash
cd backend
python3 app.py --debug  # http://localhost:8012
```
或在项目根目录用脚本（便捷重启+日志跟随）：
```bash
./restart_backend_with_logs.sh
```

### 前端（可选）
```bash
cd frontend
npm install
npm start  # http://localhost:8001
```

### 端口
- 后端: `8012`
- 前端: `8001`

## 🔧 依赖

### 后端（Python）
```bash
pip install flask flask-cors psd-tools Pillow numpy
```

### 前端（Node）
```bash
cd frontend && npm install
```

## 🔌 API 一览（实际）

- `GET /api/health`：健康检查
- `POST /api/validate`：上传 `template`(PSD) 校验是否包含必要图层 `view, part1~4`
- `POST /api/upload`：上传 `template` 入库，生成预览图、参考图、逆展开 b.psd，返回模板记录
- `GET /api/templates`：获取模板列表（读取 `storage/templates/templates.json`）
- `GET /api/templates/{id}/preview`：获取模板预览图
- `GET /api/templates/{id}/reference`：获取模板参考图
- `POST /api/templates/{id}/delete`：删除模板与相关产物
- `POST /api/generate`：表单 `templateId` + `image`，生成最终结果（final.psd + 预览图）
- `GET /api/results/{resultId}/download`：下载最终 PSD
- `GET /api/results/{resultId}/preview`：查看最终预览图
- `POST /api/process`：一次性处理（上传 `template` + `source_image`），直接返回结果PSD，不入库

## 📦 处理流程（简述）

1) 模板上传与校验：`validate_psd` 用 `psd-tools` 检查 `view, part1~4` 是否存在。
2) 模板入库：拷贝到 `storage/templates`，生成模板记录（含尺寸、view信息）。
3) 预览/参考图：
   - 预览：合并所有 `part*` 区域 alpha，50% 灰填充生成 `{tplId}_preview.png`。
   - 参考：基于 b.psd 对 `part*` 区域白填充 + 膨胀黑描边，生成 `{tplId}_reference.png`。
4) 逆展开 b.psd：`InsideTransformer` 在原尺寸画布内对 `part1/3` 水平翻转并左右移动、`part2/4` 垂直翻转并上下移动，输出 `{tplId}_restored.psd`。
5) 尺寸对齐：根据图片与模板面积，选择“缩放模板到图片”或“缩放图片到模板”。
6) 图层裁切：`PSDReplacer` 按模板 `part*` 的实际形状（alpha）从图片裁切并写回图层像素。
7) 最终变换：`BinaryPSDTransformer` 在扩展画布（≈3.5×）上移动/翻转图层，写出 final.psd，并生成最终预览图。

## 🧪 调用示例

健康检查
```bash
curl http://localhost:8012/api/health
```

上传模板并入库
```bash
curl -X POST \
  -F "template=@path/to/template.psd" \
  http://localhost:8012/api/upload
```

获取模板列表
```bash
curl http://localhost:8012/api/templates
```

基于模板生成最终结果
```bash
# 假设上一步拿到模板ID: tpl_xxx
curl -X POST \
  -F "templateId=tpl_xxx" \
  -F "image=@path/to/image.png" \
  http://localhost:8012/api/generate

# 返回JSON包含 resultId，可据此下载与预览
curl -L http://localhost:8012/api/results/<resultId>/download -o final.psd
curl -L http://localhost:8012/api/results/<resultId>/preview -o final_preview.png
```

一次性处理（不入库）
```bash
curl -X POST \
  -F "template=@path/to/template.psd" \
  -F "source_image=@path/to/source.png" \
  http://localhost:8012/api/process \
  -o result.psd
```

## 🎯 特性

- ✅ Flask REST API + CORS 支持
- ✅ 模板入库与索引管理（JSON）
- ✅ 预览/参考图自动生成
- ✅ 智能尺寸对齐（模板或图片二选一调整）
- ✅ 按图层形状的精确裁切与最终变换
- ✅ 结果预览/下载便捷

## 📝 开发状态

- ✅ 后端服务与核心逻辑已可用
- ✅ API 完整可测
- 🚧 前端界面迭代中

## 📄 许可证

MIT License

---

让 PSD 模板处理变得简单高效！🎯
