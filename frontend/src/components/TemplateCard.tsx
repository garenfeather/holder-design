import React, { useState } from 'react';
import { 
  FileText, 
  MoreVertical, 
  Download, 
  Trash2, 
  Eye, 
  Calendar,
  HardDrive,
  Layers,
  Package,
  ChevronDown
} from 'lucide-react';
import { Template } from '../types/index.ts';
import { formatFileSize, formatDate } from '../utils/index.ts';

interface TemplateCardProps {
  template: Template;
  onDelete?: (id: string) => void;
  onPreview?: (template: Template) => void;
  onUse?: (template: Template) => void;
  onUseCover?: (template: Template) => void;
  onManageComponents?: (template: Template) => void;
  className?: string;
}

export const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onDelete,
  onPreview,
  onUse,
  onUseCover,
  onManageComponents,
  className = ''
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [showUseMenu, setShowUseMenu] = useState(false);
  const [isUseButtonHovered, setIsUseButtonHovered] = useState(false);

  const getStatusColor = (status: Template['status']) => {
    switch (status) {
      case 'ready':
        return 'text-green-600 bg-green-100';
      case 'processing':
        return 'text-yellow-600 bg-yellow-100';
      case 'uploading':
        return 'text-blue-600 bg-blue-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusText = (status: Template['status']) => {
    switch (status) {
      case 'ready':
        return '就绪';
      case 'processing':
        return '处理中';
      case 'uploading':
        return '上传中';
      case 'error':
        return '错误';
      default:
        return '未知';
    }
  };

  return (
    <div className={`card-hover p-6 animate-fade-in ${className}`}>
      {/* 卡片头部 */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <FileText className="w-10 h-10 text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {template.name}
            </h3>
            <p className="text-sm text-gray-500 truncate">
              {template.fileName}
            </p>
          </div>
        </div>
        
        {/* 状态标签 */}
        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(template.status)}`}>
          {getStatusText(template.status)}
        </span>
      </div>

      {/* 模板信息 */}
      <div className="space-y-3 mb-4">
        {(template.viewLayer || template.dimensions) && (
          <div className="flex items-center text-sm text-gray-600">
            <Layers className="w-4 h-4 mr-2" />
            {template.viewLayer ? (
              <span>{template.viewLayer.width} × {template.viewLayer.height} px</span>
            ) : (
              <span>{template.dimensions?.width} × {template.dimensions?.height} px</span>
            )}
          </div>
        )}
        
        <div className="flex items-center text-sm text-gray-600">
          <HardDrive className="w-4 h-4 mr-2" />
          <span>{formatFileSize(template.size)}</span>
        </div>
        
        <div className="flex items-center text-sm text-gray-600">
          <Calendar className="w-4 h-4 mr-2" />
          <span>{formatDate(template.uploadedAt)}</span>
        </div>
        
        <div className="flex items-center text-sm text-gray-600">
          <Package className="w-4 h-4 mr-2" />
          <span>{template.components?.length || 0} 个可选部件</span>
        </div>
      </div>


      {/* 错误信息 */}
      {template.status === 'error' && template.error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{template.error}</p>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <div className="flex space-x-2 flex-1 mr-3">
          {onPreview && template.status === 'ready' && (
            <button
              onClick={() => onPreview(template)}
              className="btn-secondary text-xs py-1.5 px-2 whitespace-nowrap"
            >
              <Eye className="w-3 h-3 mr-1" />
              预览
            </button>
          )}
          
          {(onUse || onUseCover) && template.status === 'ready' && (
            <div className="relative">
              <button
                onMouseEnter={() => {
                  setIsUseButtonHovered(true);
                  setShowUseMenu(true);
                }}
                onMouseLeave={() => {
                  setIsUseButtonHovered(false);
                  // 延迟关闭菜单，让用户有时间移动到菜单项
                  setTimeout(() => {
                    if (!showUseMenu) return;
                    const menuElement = document.querySelector('.use-dropdown-menu:hover');
                    if (!menuElement) {
                      setShowUseMenu(false);
                    }
                  }, 100);
                }}
                className={`text-xs py-1.5 px-2 flex items-center whitespace-nowrap min-w-0 text-white font-medium transition-colors ${
                  showUseMenu
                    ? 'bg-primary-700 rounded-t-md'
                    : 'bg-primary-600 hover:bg-primary-700 rounded-md'
                }`}
              >
                <Download className="w-3 h-3 mr-1" />
                {isUseButtonHovered ? '生成' : '使用'}
                <ChevronDown className="w-3 h-3 ml-1" />
              </button>

              {showUseMenu && (
                <div
                  className="use-dropdown-menu absolute left-0 top-full w-full bg-primary-600 rounded-b-md shadow-elegant-lg border-t border-primary-500 z-20"
                  onMouseEnter={() => setShowUseMenu(true)}
                  onMouseLeave={() => setShowUseMenu(false)}
                >
                  {onUse && (
                    <button
                      onClick={() => {
                        setShowUseMenu(false);
                        onUse(template);
                      }}
                      className="w-full px-2 py-1.5 text-left text-xs text-white font-medium hover:bg-primary-700 transition-colors whitespace-nowrap border-b border-primary-500 last:border-b-0"
                    >
                      封底
                    </button>
                  )}
                  {onUseCover && (
                    <button
                      onClick={() => {
                        setShowUseMenu(false);
                        onUseCover(template);
                      }}
                      className="w-full px-2 py-1.5 text-left text-xs text-white font-medium hover:bg-primary-700 transition-colors whitespace-nowrap rounded-b-md"
                    >
                      封面
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
          
          {onManageComponents && template.status === 'ready' && (
            <button
              onClick={() => onManageComponents(template)}
              className="btn-secondary text-xs py-1.5 px-2 whitespace-nowrap"
            >
              <Package className="w-3 h-3 mr-1" />
              部件
            </button>
          )}
        </div>

        {/* 更多操作菜单 */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
          >
            <MoreVertical className="w-4 h-4 text-gray-400" />
          </button>

          {showMenu && (
            <>
              {/* 背景遮罩 */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              
              {/* 菜单 */}
              <div className="absolute right-0 top-full mt-1 w-32 bg-white rounded-lg shadow-elegant-lg border border-gray-200 py-1 z-20">
                {onDelete && (
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onDelete(template.id);
                    }}
                    className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center"
                  >
                    <Trash2 className="w-3 h-3 mr-2" />
                    删除
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
