from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量文件
load_dotenv()


class ProcessingConfig(BaseSettings):
    """处理相关配置常量"""

    # PSD变换配置
    CANVAS_EXPANSION_FACTOR: float = Field(3.5, description="画布扩展倍数")
    CANVAS_PADDING: int = Field(400, description="画布额外填充像素")

    # 描边配置
    DEFAULT_STROKE_WIDTH: int = Field(2, description="默认描边宽度")
    DEFAULT_STROKE_COLOR: Tuple[int, int, int, int] = Field((255, 255, 255, 255), description="默认描边颜色(R,G,B,A)")
    DEFAULT_STROKE_SMOOTH_FACTOR: float = Field(1.0, description="描边平滑因子")
    STROKE_THRESHOLD: int = Field(10, description="描边阈值")

    # 分辨率配置
    DEFAULT_DPI_H: float = Field(72.0, description="默认水平DPI")
    DEFAULT_DPI_V: float = Field(72.0, description="默认垂直DPI")
    DEFAULT_DPI_UNIT: int = Field(1, description="默认DPI单位")

    # 文件处理配置
    MAX_FILE_SIZE: int = Field(100 * 1024 * 1024, description="最大文件大小(字节)")
    TEMP_FILE_PERMISSIONS: int = Field(0o600, description="临时文件权限")

    # 图像处理配置
    DEFAULT_RGBA_COLOR: Tuple[int, int, int, int] = Field((0, 0, 0, 0), description="默认RGBA颜色(透明)")
    DEFAULT_WHITE_COLOR: Tuple[int, int, int, int] = Field((255, 255, 255, 0), description="默认白色RGBA")
    LAYER_OPACITY_MAX: int = Field(255, description="图层最大不透明度")

    # 性能配置
    LAYER_CACHE_SIZE: int = Field(100, description="图层缓存大小")
    BUFFER_SIZE: int = Field(8192, description="文件缓冲区大小")

    class Config:
        env_prefix = "PROCESSING_"
        case_sensitive = False


class AppSettings(BaseSettings):
    """应用程序配置"""

    env: Literal["development", "production", "testing"] = Field("development", description="运行环境")
    domain: str = Field("localhost", description="服务器域名")
    port: int = Field(8012, description="服务器端口")
    storage_root: str = Field("../storage", description="存储根目录")

    # 安全配置
    max_content_length: int = Field(100 * 1024 * 1024, description="最大上传文件大小")
    allowed_extensions: list[str] = Field([".psd", ".png", ".jpg", ".jpeg"], description="允许的文件扩展名")

    # 日志配置
    log_level: str = Field("INFO", description="日志级别")
    log_format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式")

    @property
    def api_base_url(self) -> str:
        """构建API基础URL"""
        return f"http://{self.domain}:{self.port}"

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_storage_root() -> Path:
    """获取存储根目录的绝对路径"""
    backend_dir = Path(__file__).parent
    storage_root = backend_dir / settings.storage_root
    return storage_root.resolve()


def get_config() -> Dict[str, str]:
    """保持向后兼容的配置获取函数"""
    return {
        "ENV": settings.env,
        "DOMAIN": settings.domain,
        "API_BASE_URL": settings.api_base_url,
        "STORAGE_ROOT": settings.storage_root,
    }


# 创建配置实例
settings = AppSettings()
processing_config = ProcessingConfig()

# 向后兼容
CONFIG = get_config()