// PSD Template Manager - 类型定义

export interface Component {
  id: string;
  name: string;
  filename: string;
  uploadedAt: Date;
  size: number;
}

export interface Template {
  id: string;
  name: string;
  fileName: string;
  size: number;
  uploadedAt: Date;
  thumbnail?: string;
  dimensions?: {
    width: number;
    height: number;
  };
  layers?: string[];
  viewLayer?: {
    width: number;
    height: number;
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
  status: 'uploading' | 'processing' | 'ready' | 'error';
  error?: string;
  components?: Component[];
  // Stroke 相关字段
  strokeConfig?: number[];  // 配置的stroke宽度数组 [2, 5, 8]
  strokeVersions?: Record<number, string>;  // stroke版本映射 {2: "filename1.psd", 5: "filename2.psd"}
  strokeCount?: number;  // stroke版本数量
}

export interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Stroke 配置相关类型
export interface StrokeConfig {
  width: number;  // stroke宽度 (1-10)
  color?: string;  // stroke颜色，默认白色
  enabled?: boolean;  // 是否启用该配置
}

export interface StrokeUploadData {
  strokeWidths: number[];  // 要生成的stroke宽度数组
}

export interface StrokeVersion {
  width: number;  // stroke宽度
  filename: string;  // 生成的文件名
  previewPath?: string;  // 预览图路径（用于编辑对比）
}

// 生成结果（基础信息，用于列表）
export interface Result {
  id: string;
  templateId: string;
  templateName: string;
  createdAt: Date;
}

// 结果详情（用于详情模态框）
export interface ResultDetail {
  id: string;
  templateId: string;
  templateName: string;
  createdAt: Date;
  finalPsdSize?: number;
  usedStrokeWidth: number | null;
  previewExists: boolean;
  psdExists: boolean;
  previewUrl?: string | null;
  downloadUrl?: string | null;
}

export interface TemplateValidationResult {
  valid: boolean;
  info?: {
    width: number;
    height: number;
    layers: string[];
  };
  error?: string;
}

export interface UploadConfig {
  maxFileSize: number; // bytes
  allowedTypes: string[];
  maxFiles: number;
}

export interface GenerateResult {
  resultId: string;
  templateId: string;
  finalPsdPath: string;
  previewPath?: string;
  generatedAt: string;
  template: Template;
  usedStrokeWidth?: number | null;
}
