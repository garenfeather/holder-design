#!/usr/bin/env bash

set -Eeuo pipefail

# Storage清理脚本 - Shell版本
# 快速清理storage目录数据，保留目录结构

echo "🧹 开始清理storage目录..."
echo "=================================================="

# 以脚本所在目录作为项目根目录
BASE_DIR="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd)"
cd "$BASE_DIR"

STORAGE_DIR="storage"

if [ ! -d "$STORAGE_DIR" ]; then
    echo "❌ Storage目录不存在: $STORAGE_DIR"
    exit 1
fi

echo "📁 Storage目录: $(pwd)/$STORAGE_DIR"
echo

# 清理函数
clean_files() {
    local dir="$1"
    local pattern="$2"
    local description="$3"

    if [ -d "$dir" ]; then
        if [ -n "$pattern" ]; then
            # 使用find删除特定模式的文件
            local count=$(find "$dir" -name "$pattern" -type f ! -name ".DS_Store" | wc -l | tr -d ' ')
            find "$dir" -name "$pattern" -type f ! -name ".DS_Store" -delete 2>/dev/null
            echo "✅ 清理 $dir ($description): 删除了 $count 个文件"
        else
            # 删除所有文件但保留目录
            local count=$(find "$dir" -type f ! -name ".DS_Store" | wc -l | tr -d ' ')
            find "$dir" -type f ! -name ".DS_Store" -delete 2>/dev/null
            echo "✅ 清理 $dir ($description): 删除了 $count 个文件"
        fi
    else
        echo "⚠️  目录不存在: $dir"
    fi
}

# 清理各个目录
clean_files "$STORAGE_DIR/templates" "*.psd" "PSD模板文件"
clean_files "$STORAGE_DIR/templates" "*.json" "JSON索引文件"
clean_files "$STORAGE_DIR/previews" "*.png" "PNG预览图"
clean_files "$STORAGE_DIR/previews" "*.jpg" "JPG预览图"
clean_files "$STORAGE_DIR/references" "*.png" "PNG参考图"
clean_files "$STORAGE_DIR/references" "*.jpg" "JPG参考图"
clean_files "$STORAGE_DIR/inside" "*.psd" "内部PSD文件"
clean_files "$STORAGE_DIR/components" "" "组件文件"
clean_files "$STORAGE_DIR/results" "" "生成结果"
clean_files "$STORAGE_DIR/cache" "" "缓存文件"

echo
echo "📝 重新创建索引文件..."

# 确保目录存在
mkdir -p "$STORAGE_DIR/templates"
mkdir -p "$STORAGE_DIR/results/downloads"
mkdir -p "$STORAGE_DIR/results/previews"
mkdir -p "$STORAGE_DIR/components"
mkdir -p "$STORAGE_DIR/cache"
mkdir -p "$STORAGE_DIR/previews"
mkdir -p "$STORAGE_DIR/references"
mkdir -p "$STORAGE_DIR/inside"

# 创建空的JSON索引文件
echo "[]" > "$STORAGE_DIR/templates/templates.json"
echo "[]" > "$STORAGE_DIR/results/results_index.json"

echo "✅ 创建索引文件: $STORAGE_DIR/templates/templates.json"
echo "✅ 创建索引文件: $STORAGE_DIR/results/results_index.json"

echo
echo "🎉 Storage清理完成！"
echo "=================================================="

# 显示目录结构
echo "📊 清理后的目录结构:"
if command -v tree >/dev/null 2>&1; then
    tree "$STORAGE_DIR" -I ".DS_Store"
else
    find "$STORAGE_DIR" -type d | sort | sed 's/[^-][^\/]*\// /g' | sed 's/^/ /' | sed 's/-/|/'
fi

echo
echo "📋 使用说明："
echo "   Shell版本:  bash ./clean_storage.sh"
echo "   或直接执行: ./clean_storage.sh"
