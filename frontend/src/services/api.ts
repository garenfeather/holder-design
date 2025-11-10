import { ApiResponse, Template, TemplateValidationResult, GenerateResult, Component, Result, ResultDetail, StrokeUploadData } from '../types/index.ts';
import { appConfig } from '../config.ts';

// 后端基础地址依赖环境配置
export const API_BASE_URL = appConfig.apiBaseUrl;

class ApiService {
  // 健康检查
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`);
      return response.ok;
    } catch {
      return false;
    }
  }

  // 上传PSD模板（支持stroke配置）
  async uploadTemplate(
    file: File,
    strokeConfig?: StrokeUploadData,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<Template>> {
    try {
      const formData = new FormData();
      formData.append('template', file);

      // 添加stroke配置（如果提供）
      if (strokeConfig && strokeConfig.strokeWidths.length > 0) {
        formData.append('strokeWidths', JSON.stringify(strokeConfig.strokeWidths));
      }

      const xhr = new XMLHttpRequest();
      
      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && onProgress) {
            const progress = Math.round((e.loaded * 100) / e.total);
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            try {
              const result = JSON.parse(xhr.responseText);
              if (result.success && result.data) {
                // 转换日期字段
                const template = {
                  ...result.data,
                  uploadedAt: new Date(result.data.uploadedAt)
                };
                resolve({
                  success: true,
                  data: template
                });
              } else {
                reject(new Error(result.error || '上传失败'));
              }
            } catch {
              reject(new Error('解析响应失败'));
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(error.error || '上传失败'));
            } catch {
              reject(new Error(`上传失败: HTTP ${xhr.status}`));
            }
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('网络错误'));
        });

        xhr.open('POST', `${API_BASE_URL}/api/upload`);
        xhr.send(formData);
      });
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '上传失败'
      };
    }
  }

  // 验证PSD模板
  async validateTemplate(file: File): Promise<TemplateValidationResult> {
    try {
      const formData = new FormData();
      formData.append('template', file);

      const response = await fetch(`${API_BASE_URL}/api/validate`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        return {
          valid: false,
          error: errorData.error || '验证失败'
        };
      }
    } catch (error) {
      return {
        valid: false,
        error: error instanceof Error ? error.message : '验证失败'
      };
    }
  }

  // 获取模板列表
  async getTemplates(): Promise<ApiResponse<Template[]>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/templates`);
      
      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data) {
          // 转换日期字段
          const templates = result.data.map((template: any) => ({
            ...template,
            uploadedAt: new Date(template.uploadedAt)
          }));
          return {
            success: true,
            data: templates
          };
        } else {
          return {
            success: false,
            error: result.error || '获取模板列表失败'
          };
        }
      } else {
        const errorData = await response.json();
        return {
          success: false,
          error: errorData.error || '获取模板列表失败'
        };
      }
    } catch (error) {
      // 如果后端API不可用，回退到本地存储
      console.warn('后端API不可用，使用本地存储:', error);
      const templates = this.getStoredTemplates();
      return {
        success: true,
        data: templates
      };
    }
  }

  // ========== 模板部件相关 ==========
  async getTemplateComponents(templateId: string): Promise<ApiResponse<Component[]>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}/components`);
      if (!response.ok) {
        return { success: false, error: '加载部件失败' };
      }
      const data = await response.json();
      return { success: true, data: data.data || [] };
    } catch {
      return { success: false, error: '网络错误' };
    }
  }

  async uploadTemplateComponent(templateId: string, file: File): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      formData.append('component', file);
      const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}/components`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        return { success: false, error: data.error || '上传失败' };
      }
      return { success: true };
    } catch {
      return { success: false, error: '网络错误' };
    }
  }

  async deleteTemplateComponent(templateId: string, componentId: string): Promise<ApiResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}/components/${componentId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        return { success: false, error: '删除失败' };
      }
      return { success: true };
    } catch {
      return { success: false, error: '网络错误' };
    }
  }

  async renameTemplateComponent(templateId: string, componentId: string, newName: string): Promise<ApiResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}/components/${componentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        return { success: false, error: data.error || '重命名失败' };
      }
      return { success: true };
    } catch {
      return { success: false, error: '网络错误' };
    }
  }

  getTemplateComponentUrl(templateId: string, componentId: string): string {
    return `${API_BASE_URL}/api/templates/${templateId}/components/${componentId}`;
  }

  // 删除模板
  async deleteTemplate(id: string): Promise<ApiResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/templates/${id}/delete`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          return {
            success: true,
            message: result.message || '模板删除成功'
          };
        } else {
          return {
            success: false,
            error: result.error || '删除模板失败'
          };
        }
      } else {
        const errorData = await response.json();
        return {
          success: false,
          error: errorData.error || '删除模板失败'
        };
      }
    } catch (error) {
      // 如果后端API不可用，回退到本地存储
      console.warn('后端API不可用，使用本地存储:', error);
      const templates = this.getStoredTemplates();
      const updatedTemplates = templates.filter(t => t.id !== id);
      localStorage.setItem('psd_templates', JSON.stringify(updatedTemplates));
      
      return {
        success: true,
        message: '模板删除成功'
      };
    }
  }

  // 本地存储相关方法
  private getStoredTemplates(): Template[] {
    try {
      const stored = localStorage.getItem('psd_templates');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  saveTemplate(template: Template): void {
    const templates = this.getStoredTemplates();
    const existingIndex = templates.findIndex(t => t.id === template.id);
    
    if (existingIndex >= 0) {
      templates[existingIndex] = template;
    } else {
      templates.unshift(template); // 新模板放在前面
    }
    
    localStorage.setItem('psd_templates', JSON.stringify(templates));
  }

  // 生成最终PSD
  async generateFinalPsd(
    templateId: string, 
    imageFile: File,
    onProgress?: (progress: number) => void,
    forceResize?: boolean,
    componentId?: string,
    strokeWidth?: number | null,
  ): Promise<ApiResponse<GenerateResult>> {
    try {
      const formData = new FormData();
      formData.append('templateId', templateId);
      formData.append('image', imageFile);
      // 统一到模板尺寸：始终对齐（后端将按模板尺寸对齐图片与模板）
      formData.append('forceResize', 'true');
      if (componentId) {
        formData.append('componentId', componentId);
      }
      if (typeof strokeWidth === 'number' && !isNaN(strokeWidth)) {
        formData.append('strokeWidth', String(strokeWidth));
      }

      const xhr = new XMLHttpRequest();
      
      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && onProgress) {
            const progress = Math.round((e.loaded * 100) / e.total);
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            try {
              const result = JSON.parse(xhr.responseText);
              if (result.success && result.data) {
                resolve({
                  success: true,
                  data: result.data,
                  message: result.message
                });
              } else {
                reject(new Error(result.error || '生成失败'));
              }
            } catch {
              reject(new Error('解析响应失败'));
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(error.error || '生成失败'));
            } catch {
              reject(new Error(`生成失败: HTTP ${xhr.status}`));
            }
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('网络错误'));
        });

        xhr.open('POST', `${API_BASE_URL}/api/generate`);
        xhr.send(formData);
      });
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '生成失败'
      };
    }
  }

  // 获取预览图URL
  getPreviewUrl(resultId: string): string {
    return `${API_BASE_URL}/api/results/${resultId}/preview`;
  }

  // 获取下载链接
  getDownloadUrl(resultId: string): string {
    return `${API_BASE_URL}/api/results/${resultId}/download`;
  }

  // 下载文件
  async downloadFile(resultId: string, filename?: string): Promise<void> {
    try {
      const response = await fetch(this.getDownloadUrl(resultId));
      
      if (!response.ok) {
        throw new Error('下载失败');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `${resultId}_final.psd`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      URL.revokeObjectURL(url);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : '下载失败');
    }
  }

  // ========== 结果管理相关（Phase 1） ==========
  async getResults(): Promise<ApiResponse<Result[]>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { success: false, error: errorData.error || '获取结果列表失败' };
      }
      const result = await response.json();
      if (result.success && Array.isArray(result.data)) {
        const items: Result[] = result.data.map((r: any) => ({
          id: r.id,
          templateId: r.templateId,
          templateName: r.templateName,
          createdAt: new Date(r.createdAt),
        }));
        return { success: true, data: items };
      }
      return { success: false, error: result.error || '获取结果列表失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // ========== 结果管理相关（Phase 2） ==========
  async getResultInfo(resultId: string): Promise<ApiResponse<ResultDetail>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results/${resultId}/info`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { success: false, error: errorData.error || '获取结果详情失败' };
      }
      const result = await response.json();
      if (result.success && result.data) {
        const d = result.data;
        const info: ResultDetail = {
          id: d.id,
          templateId: d.templateId || d.template_id,
          templateName: d.templateName || d.template_name,
          createdAt: new Date(d.createdAt || d.created_at),
          finalPsdSize: d.finalPsdSize || d.final_psd_size,
          usedStrokeWidth: d.usedStrokeWidth ?? d.used_stroke_width ?? null,
          previewExists: !!d.previewExists,
          psdExists: !!d.psdExists,
          previewUrl: d.previewUrl ?? null,
          downloadUrl: d.downloadUrl ?? null,
        };
        return { success: true, data: info };
      }
      return { success: false, error: result.error || '获取结果详情失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  async deleteResult(resultId: string): Promise<ApiResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results/${resultId}/delete`, { method: 'DELETE' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        return { success: false, error: data.error || '删除失败' };
      }
      const data = await response.json().catch(() => ({}));
      return { success: !!data.success, message: data.message };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  async deleteResultsBulk(resultIds: string[]): Promise<{ ok: string[]; failed: string[] }>{
    const outcomes = await Promise.allSettled(resultIds.map(id => this.deleteResult(id)));
    const ok: string[] = [];
    const failed: string[] = [];
    outcomes.forEach((res, idx) => {
      const id = resultIds[idx];
      if (res.status === 'fulfilled' && res.value.success) ok.push(id);
      else failed.push(id);
    });
    return { ok, failed };
  }

  async cleanupResults(options: { keepRecent?: number; olderThanDays?: number; dryRun?: boolean }): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results/cleanup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options || {}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.success) {
        return { success: false, error: data.error || '清理失败' };
      }
      return { success: true, data };
    } catch {
      return { success: false, error: '网络错误' };
    }
  }

  // ========== 刀模系统API ==========

  // 通用GET方法
  async get(url: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`);
      if (response.ok) {
        const result = await response.json();
        return result.success ? { success: true, data: result.data, message: result.message } : { success: false, error: result.error, message: result.message };
      }
      const errorData = await response.json().catch(() => ({}));
      return { success: false, error: errorData.error || '请求失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 通用POST方法
  async post(url: string, data: any): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (response.ok && result.success) {
        return { success: true, data: result.data, message: result.message };
      }
      return { success: false, error: result.error || '请求失败', message: result.message };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 通用PUT方法
  async put(url: string, data: any): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (response.ok && result.success) {
        return { success: true, data: result.data, message: result.message };
      }
      return { success: false, error: result.error || '请求失败', message: result.message };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 通用DELETE方法
  async delete(url: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (response.ok && result.success) {
        return { success: true, data: result.data, message: result.message };
      }
      return { success: false, error: result.error || '请求失败', message: result.message };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 获取刀模元素列表
  async getDieElements(): Promise<ApiResponse<any[]>> {
    return this.get('/api/die-elements');
  }

  // 创建刀模元素
  async createDieElement(data: {
    name: string;
    cutSize: { width: number; height: number };
    referenceSize: { width: number; height: number };
  }): Promise<ApiResponse<any>> {
    return this.post('/api/die-elements', data);
  }

  // 更新刀模元素
  async updateDieElement(elementId: string, data: {
    name?: string;
    cutSize?: { width: number; height: number };
    referenceSize?: { width: number; height: number };
  }): Promise<ApiResponse<any>> {
    return this.put(`/api/die-elements/${elementId}`, data);
  }

  // 删除刀模元素
  async deleteDieElement(elementId: string): Promise<ApiResponse<any>> {
    return this.delete(`/api/die-elements/${elementId}`);
  }

  // 生成刀模素材（上传图片）
  async generateDieMaterial(elementId: string, imageFile: File): Promise<ApiResponse<any>> {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await fetch(`${API_BASE_URL}/api/die-elements/${elementId}/generate`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      if (response.ok && result.success) {
        return { success: true, data: result.data };
      }
      return { success: false, error: result.error || '生成刀模素材失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 获取刀模素材列表（可选分组）
  async getDieMaterials(options?: { elementId?: string; grouped?: boolean }): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams();
      if (options?.elementId) params.append('elementId', options.elementId);
      if (options?.grouped) params.append('grouped', 'true');

      const url = `${API_BASE_URL}/api/die-materials${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);

      if (response.ok) {
        const result = await response.json();
        return result.success ? { success: true, data: result.data } : { success: false, error: result.error };
      }
      return { success: false, error: '获取刀模素材列表失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // 获取刀模素材文件URL，支持旋转后临时预览
  getDieMaterialUrl(materialId: string, options?: { rotate?: number }): string {
    const params = new URLSearchParams();

    if (options?.rotate !== undefined) {
      const normalized = ((options.rotate % 360) + 360) % 360;
      if (normalized !== 0) {
        params.set('rotate', normalized.toString());
      }
    }

    const query = params.toString();
    return `${API_BASE_URL}/api/die-materials/${materialId}${query ? `?${query}` : ''}`;
  }

  // 删除刀模素材
  async deleteDieMaterial(materialId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/die-materials/${materialId}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (response.ok && result.success) {
        return { success: true, data: result };
      }
      return { success: false, error: result.error || '删除刀模素材失败' };
    } catch (e) {
      return { success: false, error: '网络错误' };
    }
  }

  // ========== 布局模版API ==========

  // 创建布局模版
  async createLayoutTemplate(data: {
    name: string;
    paperSize: string;
    paperOrientation: string;
    elements: any[];
    previewImage?: string;
  }): Promise<ApiResponse<any>> {
    return this.post('/api/layout-templates', data);
  }

  // 获取所有布局模版
  async getLayoutTemplates(): Promise<ApiResponse<any[]>> {
    return this.get('/api/layout-templates');
  }

  // 获取单个布局模版
  async getLayoutTemplate(templateId: string): Promise<ApiResponse<any>> {
    return this.get(`/api/layout-templates/${templateId}`);
  }

  // 删除布局模版
  async deleteLayoutTemplate(templateId: string): Promise<ApiResponse<any>> {
    return this.delete(`/api/layout-templates/${templateId}`);
  }

  // ============================================================
  // 排版成品API
  // ============================================================

  // 创建排版成品
  async createPrintArrangement(templateId: string, materialMappings: Record<string, string>): Promise<ApiResponse<any>> {
    return this.post('/api/print-arrangements', {
      templateId,
      materialMappings
    });
  }

  // 获取所有排版成品
  async getPrintArrangements(): Promise<ApiResponse<any>> {
    return this.get('/api/print-arrangements');
  }

  // 获取排版成品预览图URL
  getPrintArrangementPreviewUrl(arrangementId: string): string {
    return `${API_BASE_URL}/api/print-arrangements/${arrangementId}/preview`;
  }

  // 获取排版成品下载URL
  getPrintArrangementDownloadUrl(arrangementId: string): string {
    return `${API_BASE_URL}/api/print-arrangements/${arrangementId}/download`;
  }

  // 删除排版成品
  async deletePrintArrangement(arrangementId: string): Promise<ApiResponse<any>> {
    return this.delete(`/api/print-arrangements/${arrangementId}`);
  }

}

export const apiService = new ApiService();
