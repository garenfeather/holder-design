import React, { useState, useEffect } from 'react';
import { Image, Download, Trash2, Eye, CheckSquare, Square, ChevronDown, ChevronRight } from 'lucide-react';
import { apiService } from '../services/api.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { ResultDetailModal } from './ResultDetailModal.tsx';

interface DieMaterial {
  id: string;
  elementId: string;
  elementName: string;
  fileName: string;
  filePath: string;
  cutSize: {
    width: number;
    height: number;
  };
  referenceSize: {
    width: number;
    height: number;
  };
  createdAt: string;
}

interface GroupedMaterials {
  [elementId: string]: {
    elementName: string;
    cutSize: { width: number; height: number };
    referenceSize: { width: number; height: number };
    materials: DieMaterial[];
  };
}

export const DieMaterialManager: React.FC = () => {
  const [groupedMaterials, setGroupedMaterials] = useState<GroupedMaterials>({});
  const [loading, setLoading] = useState(true);
  const [selectedMaterials, setSelectedMaterials] = useState<Set<string>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; material: DieMaterial | null }>({
    show: false,
    material: null,
  });
  const [previewMaterial, setPreviewMaterial] = useState<DieMaterial | null>(null);

  // 加载素材数据
  const loadMaterials = async () => {
    setLoading(true);
    try {
      const response = await apiService.getDieMaterials({ grouped: true });
      if (response.success && response.data) {
        setGroupedMaterials(response.data);
        // 默认展开所有分组
        setExpandedGroups(new Set(Object.keys(response.data)));
      }
    } catch (error) {
      console.error('加载刀模素材列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, []);

  // 切换分组展开/折叠
  const toggleGroup = (elementId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(elementId)) {
      newExpanded.delete(elementId);
    } else {
      newExpanded.add(elementId);
    }
    setExpandedGroups(newExpanded);
  };

  // 切换素材选择
  const toggleMaterialSelection = (materialId: string) => {
    const newSelected = new Set(selectedMaterials);
    if (newSelected.has(materialId)) {
      newSelected.delete(materialId);
    } else {
      newSelected.add(materialId);
    }
    setSelectedMaterials(newSelected);
  };

  // 删除素材
  const handleDeleteClick = (material: DieMaterial) => {
    setDeleteConfirm({ show: true, material });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm.material) return;

    try {
      const response = await apiService.deleteDieMaterial(deleteConfirm.material.id);
      if (response.success) {
        await loadMaterials();
        // 如果被删除的素材在选中列表中，移除它
        const newSelected = new Set(selectedMaterials);
        newSelected.delete(deleteConfirm.material.id);
        setSelectedMaterials(newSelected);
      }
    } catch (error) {
      console.error('删除素材失败:', error);
    } finally {
      setDeleteConfirm({ show: false, material: null });
    }
  };

  // 下载素材
  const handleDownload = (material: DieMaterial) => {
    const url = apiService.getDieMaterialUrl(material.id);
    const link = document.createElement('a');
    link.href = url;
    link.download = material.fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 预览素材
  const handlePreview = (material: DieMaterial) => {
    setPreviewMaterial(material);
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">生成刀模素材管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            按元素分组管理已生成的刀模素材
          </p>
        </div>
        {selectedMaterials.size > 0 && (
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-600">
              已选择 {selectedMaterials.size} 个素材
            </span>
            <button
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              onClick={() => {
                // TODO: 在阶段4实现跳转到排版功能
                console.log('用于排版:', Array.from(selectedMaterials));
              }}
            >
              用于排版
            </button>
          </div>
        )}
      </div>

      {/* 素材分组列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-gray-500">加载中...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.keys(groupedMaterials).length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <Image className="w-16 h-16 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                还没有生成素材
              </h3>
              <p className="text-gray-500">
                前往刀模元素管理创建元素并生成素材
              </p>
            </div>
          ) : (
            Object.entries(groupedMaterials).map(([elementId, group]) => (
              <div
                key={elementId}
                className="bg-white border border-gray-200 rounded-xl overflow-hidden"
              >
                {/* 分组头部 */}
                <div
                  className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors flex items-center justify-between"
                  onClick={() => toggleGroup(elementId)}
                >
                  <div className="flex items-center space-x-3">
                    <div className="text-gray-500">
                      {expandedGroups.has(elementId) ? (
                        <ChevronDown className="w-5 h-5" />
                      ) : (
                        <ChevronRight className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{group.elementName}</h3>
                      <div className="text-sm text-gray-600 mt-1">
                        裁切: {group.cutSize.width} × {group.cutSize.height} cm |
                        参考: {group.referenceSize.width} × {group.referenceSize.height} cm |
                        共 {group.materials.length} 个素材
                      </div>
                    </div>
                  </div>
                </div>

                {/* 素材网格 */}
                {expandedGroups.has(elementId) && (
                  <div className="p-4 grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                    {group.materials.map((material) => (
                      <div
                        key={material.id}
                        className="relative group bg-gray-50 rounded-lg overflow-hidden border border-gray-200"
                      >
                        {/* 选择框 */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleMaterialSelection(material.id);
                          }}
                          className="absolute top-1 left-1 z-10 p-0.5 bg-white rounded shadow-sm hover:bg-gray-50"
                        >
                          {selectedMaterials.has(material.id) ? (
                            <CheckSquare className="w-4 h-4 text-primary-600" />
                          ) : (
                            <Square className="w-4 h-4 text-gray-400" />
                          )}
                        </button>

                        {/* 素材预览 */}
                        <div className="aspect-square bg-gray-200 flex items-center justify-center">
                          <img
                            src={apiService.getDieMaterialUrl(material.id)}
                            alt={material.fileName}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              // 图片加载失败时显示占位图标
                              e.currentTarget.style.display = 'none';
                              e.currentTarget.parentElement!.innerHTML = '<svg class="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>';
                            }}
                          />
                        </div>

                        {/* 操作按钮（悬停显示） */}
                        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePreview(material);
                              }}
                              className="p-1.5 bg-white rounded hover:bg-gray-100 transition-colors"
                              title="预览"
                            >
                              <Eye className="w-3 h-3 text-gray-700" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownload(material);
                              }}
                              className="p-1.5 bg-white rounded hover:bg-gray-100 transition-colors"
                              title="下载"
                            >
                              <Download className="w-3 h-3 text-gray-700" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteClick(material);
                              }}
                              className="p-1.5 bg-white rounded hover:bg-red-50 transition-colors"
                              title="删除"
                            >
                              <Trash2 className="w-3 h-3 text-red-600" />
                            </button>
                          </div>
                        </div>

                        {/* 文件名 */}
                        <div className="p-1.5 text-xs text-gray-600 truncate bg-white">
                          {material.fileName}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* 删除确认对话框 */}
      {deleteConfirm.show && deleteConfirm.material && (
        <ConfirmDialog
          isOpen={deleteConfirm.show}
          title="删除刀模素材"
          message={`确定要删除素材"${deleteConfirm.material.fileName}"吗？此操作无法恢复。`}
          confirmText="删除"
          cancelText="取消"
          onConfirm={confirmDelete}
          onCancel={() => setDeleteConfirm({ show: false, material: null })}
          type="danger"
        />
      )}

      {/* 预览模态框 */}
      {previewMaterial && (
        <ResultDetailModal
          isOpen={true}
          onClose={() => setPreviewMaterial(null)}
          result={{
            id: previewMaterial.id,
            templateId: '',
            templateName: previewMaterial.elementName,
            fileName: previewMaterial.fileName,
            filePath: previewMaterial.filePath,
            createdAt: previewMaterial.createdAt,
          }}
          customImageUrl={apiService.getDieMaterialUrl(previewMaterial.id)}
        />
      )}
    </div>
  );
};
