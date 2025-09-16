import React, { useState, useEffect } from 'react';
import { 
  Grid3X3, 
  List, 
  Plus, 
  Package,
  RefreshCw
} from 'lucide-react';
import { Template } from '../types/index.ts';
import { TemplateCard } from './TemplateCard.tsx';
import { UseModal } from './UseModal.tsx';
import { ComponentModal } from './ComponentModal.tsx';
import { apiService } from '../services/api.ts';

interface TemplateBoxProps {
  onCreateNew?: () => void;
  onTemplateSelect?: (template: Template) => void;
  onTemplatePreview?: (template: Template) => void;
  refreshTrigger?: number; // 用于触发刷新的计数器
  className?: string;
}

type ViewMode = 'grid' | 'list';

export const TemplateBox: React.FC<TemplateBoxProps> = ({
  onCreateNew,
  onTemplateSelect,
  onTemplatePreview,
  refreshTrigger,
  className = ''
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [isUseModalOpen, setIsUseModalOpen] = useState(false);
  const [isComponentModalOpen, setIsComponentModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [componentTemplate, setComponentTemplate] = useState<Template | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  // 当刷新触发器变化时重新加载模板
  useEffect(() => {
    if (refreshTrigger !== undefined) {
      loadTemplates();
    }
  }, [refreshTrigger]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const result = await apiService.getTemplates();
      if (result.success && result.data) {
        setTemplates(result.data);
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm('确定要删除这个模板吗？此操作无法撤销。')) {
      return;
    }

    try {
      const result = await apiService.deleteTemplate(id);
      if (result.success) {
        setTemplates(prev => prev.filter(t => t.id !== id));
      }
    } catch (error) {
      console.error('Failed to delete template:', error);
    }
  };

  const handlePreviewTemplate = (template: Template) => {
    onTemplatePreview?.(template);
  };

  const handleUseTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setIsUseModalOpen(true);
  };

  const handleUseCoverTemplate = (template: Template) => {
    // TODO: 这里将来需要打开封面模态框或设置模式
    // 暂时用同样的UseModal，但可以传递一个mode参数
    setSelectedTemplate(template);
    setIsUseModalOpen(true);
    console.log('封面功能待实现', template);
  };

  const handleGenerateComplete = () => {
    // 生成完成后可以刷新模板列表或执行其他操作
    console.log('生成完成');
  };

  const handleManageComponents = (template: Template) => {
    setComponentTemplate(template);
    setIsComponentModalOpen(true);
  };

  const handleComponentUpdate = () => {
    // 部件更新后刷新模板列表
    loadTemplates();
  };

  // 按最新上传时间排序模板
  const sortedTemplates = templates.sort((a, b) => {
    return new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime();
  });

  const renderEmptyState = () => (
    <div className="text-center py-12 animate-fade-in">
      <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        还没有模板
      </h3>
      <p className="text-gray-500 mb-6 max-w-md mx-auto">
        开始上传您的第一个 PSD 模板，建立您的模板库。
      </p>
      {onCreateNew && (
        <button
          onClick={onCreateNew}
          className="btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          上传模板
        </button>
      )}
    </div>
  );

  const renderViewControls = () => (
    <div className="flex items-center justify-between mb-6">
      <div></div> {/* 空占位符保持布局 */}
      
      <div className="flex items-center space-x-4">
        {/* 视图模式切换 */}
        <div className="flex border border-gray-300 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded ${
              viewMode === 'grid'
                ? 'bg-primary-600 text-white'
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded ${
              viewMode === 'list'
                ? 'bg-primary-600 text-white'
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        {/* 刷新按钮 */}
        <button
          onClick={loadTemplates}
          className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </div>
  );

  const renderTemplateGrid = () => (
    <div className={`
      ${viewMode === 'grid' 
        ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6' 
        : 'space-y-4'
      }
    `}>
      {sortedTemplates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          onDelete={handleDeleteTemplate}
          onPreview={handlePreviewTemplate}
          onUse={handleUseTemplate}
          onUseCover={handleUseCoverTemplate}
          onManageComponents={handleManageComponents}
          className={viewMode === 'list' ? 'max-w-none' : ''}
        />
      ))}
    </div>
  );

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">模板箱子</h2>
          <p className="text-gray-600 mt-1">
            {loading ? '加载中...' : `共 ${sortedTemplates.length} 个模板`}
          </p>
        </div>
        
        {onCreateNew && (
          <button
            onClick={onCreateNew}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            上传新模板
          </button>
        )}
      </div>

      {/* 视图控制 */}
      {templates.length > 0 && renderViewControls()}

      {/* 内容区域 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
          <span className="ml-3 text-gray-600">加载模板中...</span>
        </div>
      ) : sortedTemplates.length === 0 ? (
        renderEmptyState()
      ) : (
        renderTemplateGrid()
      )}
      
      {/* 使用模态框 */}
      <UseModal
        isOpen={isUseModalOpen}
        onClose={() => setIsUseModalOpen(false)}
        template={selectedTemplate}
        onGenerate={handleGenerateComplete}
      />
      
      {/* 部件管理模态框 */}
      <ComponentModal
        isOpen={isComponentModalOpen}
        onClose={() => setIsComponentModalOpen(false)}
        template={componentTemplate}
        onComponentUpdate={handleComponentUpdate}
      />
    </div>
  );
};