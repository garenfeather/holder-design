import React, { useState, useRef, useEffect } from 'react';
import { X, Upload, Trash2, Edit3, Package } from 'lucide-react';
import { Template, Component } from '../types/index.ts';
import { apiService } from '../services/api.ts';
import { formatFileSize, formatDate } from '../utils/index.ts';

interface ComponentModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: Template | null;
  onComponentUpdate?: () => void;
}

export const ComponentModal: React.FC<ComponentModalProps> = ({
  isOpen,
  onClose,
  template,
  onComponentUpdate
}) => {
  const [components, setComponents] = useState<Component[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && template) {
      loadComponents();
    }
  }, [isOpen, template]);

  const loadComponents = async () => {
    if (!template) return;
    
    setIsLoading(true);
    try {
      const res = await apiService.getTemplateComponents(template.id);
      if (res.success && res.data) {
        setComponents(res.data);
      } else {
        setError(res.error || '加载部件失败');
      }
    } catch (err) {
      setError('网络错误');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!template || !event.target.files?.length) return;
    
    const file = event.target.files[0];
    if (!file.type.startsWith('image/png')) {
      setError('只支持PNG格式文件');
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('component', file);

    try {
      const res = await apiService.uploadTemplateComponent(template.id, file);
      if (res.success) {
        await loadComponents();
        onComponentUpdate?.();
      } else {
        setError(res.error || '上传失败');
      }
    } catch (err) {
      setError('网络错误');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (componentId: string) => {
    if (!template || !confirm('确定要删除这个部件吗？')) return;

    try {
      const res = await apiService.deleteTemplateComponent(template.id, componentId);
      if (res.success) {
        await loadComponents();
        onComponentUpdate?.();
      } else {
        setError(res.error || '删除失败');
      }
    } catch (err) {
      setError('网络错误');
    }
  };

  const handleRename = async (componentId: string, newName: string) => {
    if (!template || !newName.trim()) return;

    try {
      const res = await apiService.renameTemplateComponent(template.id, componentId, newName);
      if (res.success) {
        await loadComponents();
        setEditingId(null);
        setEditingName('');
      } else {
        setError(res.error || '重命名失败');
      }
    } catch (err) {
      setError('网络错误');
    }
  };

  const startEdit = (component: Component) => {
    setEditingId(component.id);
    setEditingName(component.name);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  if (!isOpen || !template) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-elegant-xl max-w-4xl max-h-[90vh] w-full mx-4 flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              管理部件
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {template.name} - 共 {components.length} 个部件
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 上传区域 */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center space-x-4">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png"
              onChange={handleUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="btn-primary flex items-center space-x-2"
            >
              <Upload className="w-4 h-4" />
              <span>{isUploading ? '上传中...' : '上传部件'}</span>
            </button>
            <div className="text-sm text-gray-500">
              只支持PNG格式，尺寸必须为 {template.viewLayer?.width} × {template.viewLayer?.height} px
            </div>
          </div>
          
          {error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* 部件列表 */}
        <div className="flex-1 p-6 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-gray-500">加载中...</div>
            </div>
          ) : components.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-center text-gray-500">
                <Package className="w-12 h-12 mx-auto mb-2" />
                <p>暂无部件</p>
                <p className="text-sm">点击上方按钮添加第一个部件</p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {components
                .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())
                .map((component) => (
                <div key={component.id} className="bg-white border border-gray-200 rounded-lg">
                  {/* 部件标题和操作 */}
                  <div className="flex items-center justify-between p-4 border-b border-gray-100">
                    <div className="flex-1">
                      {editingId === component.id ? (
                        <div className="flex items-center space-x-3">
                          <input
                            type="text"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            className="flex-1 text-lg font-medium px-3 py-2 border border-gray-300 rounded"
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                handleRename(component.id, editingName);
                              } else if (e.key === 'Escape') {
                                cancelEdit();
                              }
                            }}
                            autoFocus
                          />
                          <button
                            onClick={() => handleRename(component.id, editingName)}
                            className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                          >
                            确定
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                          >
                            取消
                          </button>
                        </div>
                      ) : (
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">{component.name}</h3>
                          <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                            <span>{formatFileSize(component.size)}</span>
                            <span>上传于 {formatDate(component.uploadedAt)}</span>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {editingId !== component.id && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => startEdit(component)}
                          className="px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center space-x-2"
                        >
                          <Edit3 className="w-4 h-4" />
                          <span>编辑</span>
                        </button>
                        <button
                          onClick={() => handleDelete(component.id)}
                          className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 flex items-center space-x-2"
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>删除</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* 预览图 */}
                  <div className="p-4">
                    <div 
                      className="relative rounded-lg overflow-hidden"
                      style={{
                        aspectRatio: `${template.viewLayer?.width || 1} / ${template.viewLayer?.height || 1}`,
                        width: '100%',
                        backgroundColor: 'rgb(128, 128, 128)'
                      }}
                    >
                      <div className="absolute inset-2">
                        <img
                          src={apiService.getTemplateComponentUrl(template.id, component.id)}
                          alt={component.name}
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            const img = e.target as HTMLImageElement;
                            img.style.display = 'none';
                            const errorDiv = img.parentElement?.querySelector('.component-error-placeholder');
                            if (errorDiv) {
                              (errorDiv as HTMLElement).style.display = 'flex';
                            }
                          }}
                          onLoad={(e) => {
                            const img = e.target as HTMLImageElement;
                            const errorDiv = img.parentElement?.querySelector('.component-error-placeholder');
                            if (errorDiv) {
                              (errorDiv as HTMLElement).style.display = 'none';
                            }
                          }}
                        />
                      </div>
                      
                      {/* 错误占位符 */}
                      <div className="component-error-placeholder absolute inset-0 hidden items-center justify-center">
                        <div className="text-center text-gray-200">
                          <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <p>部件预览图加载失败</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                ))}
            </div>
          )}
        </div>

        {/* 底部信息 */}
        <div className="px-6 py-4 bg-gray-50 rounded-b-xl border-t border-gray-200">
          <div className="text-sm text-gray-600">
            部件要求：PNG格式，尺寸 {template.viewLayer?.width} × {template.viewLayer?.height} px
          </div>
        </div>
      </div>
    </div>
  );
};
