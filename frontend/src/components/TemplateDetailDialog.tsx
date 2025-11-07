import React from 'react';
import { X, Trash2 } from 'lucide-react';
import { LayoutTemplate } from '../types/index.ts';

interface TemplateDetailDialogProps {
  isOpen: boolean;
  template: LayoutTemplate | null;
  onClose: () => void;
  onDelete: (templateId: string) => void;
}

export const TemplateDetailDialog: React.FC<TemplateDetailDialogProps> = ({
  isOpen,
  template,
  onClose,
  onDelete,
}) => {
  if (!isOpen || !template) return null;

  // 统计每个元素的出现次数
  const elementStats: { [elementId: string]: { name: string; size: string; count: number } } = {};

  template.elements.forEach((element) => {
    if (!elementStats[element.elementId]) {
      elementStats[element.elementId] = {
        name: element.elementName,
        size: `${element.cutSize.width} × ${element.cutSize.height} cm`,
        count: 0,
      };
    }
    elementStats[element.elementId].count++;
  });

  const stats = Object.values(elementStats);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">模版详情</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="grid grid-cols-2 gap-6">
            {/* 左侧：预览图 */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">预览图</h3>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <img
                  src={template.previewImage}
                  alt={template.name}
                  className="w-full h-auto"
                />
              </div>
            </div>

            {/* 右侧：信息和统计 */}
            <div className="space-y-6">
              {/* 基本信息 */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">基本信息</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">名称：</span>
                    <span className="font-medium text-gray-900">{template.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">纸张大小：</span>
                    <span className="font-medium text-gray-900">{template.paperSize}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">方向：</span>
                    <span className="font-medium text-gray-900">
                      {template.paperOrientation === 'landscape' ? '横向' : '纵向'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">创建时间：</span>
                    <span className="font-medium text-gray-900">
                      {new Date(template.createdAt).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">元素总数：</span>
                    <span className="font-medium text-gray-900">{template.elements.length}</span>
                  </div>
                </div>
              </div>

              {/* 元素统计 */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">元素统计</h3>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">元素名称</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">尺寸</th>
                        <th className="px-4 py-2 text-center font-medium text-gray-700">数量</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {stats.map((stat, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-2">{stat.name}</td>
                          <td className="px-4 py-2 text-gray-600">{stat.size}</td>
                          <td className="px-4 py-2 text-center font-medium">{stat.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200">
          <button
            onClick={() => {
              if (window.confirm(`确定要删除模版"${template.name}"吗？`)) {
                onDelete(template.id);
              }
            }}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span>删除模版</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
