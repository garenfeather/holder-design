#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字符串工具：统一的不可见字符过滤与名称清理

提供 sanitize_name，用于在任何图层检测、文件生成、保存修改等涉及字符串的操作前，
统一清洗不可见字符，去除空字节和控制字符（保留\t/\n/\r），并去除首尾空白。
"""

from typing import Optional


def sanitize_name(name: Optional[str]) -> str:
    """清理名称字符串：去除不可见字符与空字节，标准化后返回。

    - 去除空字节 (\x00)
    - 去除除 \t、\n、\r 以外的控制字符 (ord(c) < 32)
    - 去除首尾空白
    - 为空时返回 'unnamed_layer'
    """
    if not name:
        return "unnamed_layer"

    # 移除空字节
    cleaned = name.replace("\x00", "")
    # 过滤控制字符（保留 \t/\n/\r）
    cleaned = "".join(ch for ch in cleaned if (ord(ch) >= 32) or (ch in "\t\n\r"))
    # 去除首尾空白
    cleaned = cleaned.strip()
    if not cleaned:
        return "unnamed_layer"
    return cleaned

