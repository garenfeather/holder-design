import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { apiService } from '../services/api.ts';

interface MaterialSelectionDialogProps {
  isOpen: boolean;
  elementId: string;
  elementName: string;
  currentLayoutElementId: string;
  onClose: () => void;
  onSelect: (materialId: string, option: 'current' | 'all' | 'unassigned') => void;
}

interface DieMaterial {
  id: string;
  fileName: string;
  filePath: string;
}

export const MaterialSelectionDialog: React.FC<MaterialSelectionDialogProps> = ({
  isOpen,
  elementId,
  elementName,
  currentLayoutElementId,
  onClose,
  onSelect,
}) => {
  const [materials, setMaterials] = useState<DieMaterial[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<'current' | 'all' | 'unassigned'>('current');

  useEffect(() => {
    if (isOpen && elementId) {
      loadMaterials();
    }
  }, [isOpen, elementId]);

  const loadMaterials = async () => {
    setLoading(true);
    try {
      const response = await apiService.getDieMaterials({ elementId });
      if (response.success && response.data) {
        setMaterials(response.data);
      }
    } catch (error) {
      console.error('加载素材失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (selectedMaterial) {
      onSelect(selectedMaterial, selectedOption);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">选择素材</h2>
            <p className="text-sm text-gray-500 mt-1">{elementName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : materials.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p>该元素暂无可用素材</p>
              <p className="text-sm mt-2">请先在刀模元素管理中生成素材</p>
            </div>
          ) : (
            <div>
              {/* 素材网格 */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {materials.map((material) => (
                  <div
                    key={material.id}
                    onClick={() => setSelectedMaterial(material.id)}
                    className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                      selectedMaterial === material.id
                        ? 'border-primary-600 ring-2 ring-primary-200'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <div className="aspect-square bg-gray-100 flex items-center justify-center">
                      <img
                        src={apiService.getDieMaterialUrl(material.id)}
                        alt={material.fileName}
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <div className="p-2 text-xs text-gray-600 truncate bg-white">
                      {material.fileName}
                    </div>
                    {selectedMaterial === material.id && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* 填充选项 */}
              {selectedMaterial && (
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <h3 className="text-sm font-medium text-gray-900 mb-3">填充选项：</h3>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="fillOption"
                        value="current"
                        checked={selectedOption === 'current'}
                        onChange={() => setSelectedOption('current')}
                        className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700">仅填入当前元素</span>
                    </label>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="fillOption"
                        value="all"
                        checked={selectedOption === 'all'}
                        onChange={() => setSelectedOption('all')}
                        className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700">画布上所有同元素均填入该素材</span>
                    </label>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="fillOption"
                        value="unassigned"
                        checked={selectedOption === 'unassigned'}
                        onChange={() => setSelectedOption('unassigned')}
                        className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700">画布上尚未选择的同元素均填入该素材</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedMaterial}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
};
