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
}
