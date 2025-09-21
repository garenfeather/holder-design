import React from 'react';
import { X } from 'lucide-react';
import { Template } from '../types/index.ts';
import { API_BASE_URL } from '../services/api.ts';

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: Template | null;
}

export const PreviewModal: React.FC<PreviewModalProps> = ({
  isOpen,
  onClose,
  template
}) => {
  if (!isOpen || !template) return null;

  const previewImageUrl = `${API_BASE_URL}/api/templates/${template.id}/preview`;
  const referenceImageUrl = `${API_BASE_URL}/api/templates/${template.id}/reference`;

  return (
    <div className="fixed inset-0 bg-white/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-elegant-xl max-w-4xl max-h-[90vh] w-full mx-4 flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              模板预览
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {template.name} - {template.fileName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 预览图区域 */}
        <div className="flex-1 p-6 overflow-auto">
          <div className="flex justify-center">
            <div className="w-full space-y-6">
              {/* Stroke 提示栏 */}
              {template.strokeConfig && template.strokeConfig.length > 0 && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700">
                  支持的描边版本：{[...template.strokeConfig].sort((a, b) => a - b).join('px, ')}px（共 {template.strokeConfig.length} 个）
                </div>
              )}

              {/* 模板预览 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">模板预览</h3>
                <div className="border border-gray-200 rounded-lg p-3 bg-white">
                  <img
                    src={previewImageUrl}
                    alt={`${template.name} 预览图`}
                    className="w-full h-auto object-contain rounded"
                    onError={(e) => {
                      const img = e.target as HTMLImageElement;
                      img.style.display = 'none';
                      const errorDiv = img.parentElement?.parentElement?.querySelector('.error-placeholder');
                      if (errorDiv) {
                        (errorDiv as HTMLElement).style.display = 'flex';
                      }
                    }}
                    onLoad={(e) => {
                      const img = e.target as HTMLImageElement;
                      const errorDiv = img.parentElement?.parentElement?.querySelector('.error-placeholder');
                      if (errorDiv) {
                        (errorDiv as HTMLElement).style.display = 'none';
                      }
                    }}
                  />
                </div>
                
                {/* 错误占位符 */}
                <div className="error-placeholder flex items-center justify-center w-full h-64 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300">
                  <div className="text-center">
                    <div className="text-gray-400 mb-2">
                      <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="text-gray-500">预览图加载失败</p>
                    <p className="text-sm text-gray-400">可能需要重新生成预览图</p>
                  </div>
                </div>
              </div>

              {/* 参考图预览 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">参考图预览</h3>
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-500">
                  <img
                    src={referenceImageUrl}
                    alt={`${template.name} 参考图`}
                    className="w-full h-auto object-contain rounded"
                    onError={(e) => {
                      const img = e.target as HTMLImageElement;
                      img.style.display = 'none';
                      const errorDiv = img.parentElement?.parentElement?.querySelector('.reference-error-placeholder');
                      if (errorDiv) {
                        (errorDiv as HTMLElement).style.display = 'flex';
                      }
                    }}
                    onLoad={(e) => {
                      const img = e.target as HTMLImageElement;
                      const errorDiv = img.parentElement?.parentElement?.querySelector('.reference-error-placeholder');
                      if (errorDiv) {
                        (errorDiv as HTMLElement).style.display = 'none';
                      }
                    }}
                  />
                </div>
                
                {/* 参考图错误占位符 */}
                <div className="reference-error-placeholder flex items-center justify-center w-full h-64 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300">
                  <div className="text-center">
                    <div className="text-gray-400 mb-2">
                      <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="text-gray-500">参考图加载失败</p>
                    <p className="text-sm text-gray-400">可能需要重新生成参考图</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 底部信息 */}
        <div className="px-6 py-4 bg-gray-50 rounded-b-xl border-t border-gray-200">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center space-x-4">
              <span>尺寸: {template.dimensions?.width} × {template.dimensions?.height} px</span>
              <span>大小: {(template.size / 1024 / 1024).toFixed(1)} MB</span>
              {template.strokeConfig && template.strokeConfig.length > 0 && (
                <span className="text-blue-600 font-medium">
                  描边版本: {template.strokeConfig.join('px, ')}px ({template.strokeConfig.length}个)
                </span>
              )}
            </div>
            <div>
              上传时间: {new Date(template.uploadedAt).toLocaleString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
