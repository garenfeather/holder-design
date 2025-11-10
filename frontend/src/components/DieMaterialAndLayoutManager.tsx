import React, { useState, useEffect } from 'react';
import { Image, Trash2, ChevronDown, ChevronRight, Layout, Download, FileText } from 'lucide-react';
import { apiService } from '../services/api.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { TemplateDetailDialog } from './TemplateDetailDialog.tsx';
import { LayoutTemplateUpload } from './LayoutTemplateUpload.tsx';
import { LayoutTemplate, PrintArrangement } from '../types/index.ts';

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

interface Props {
  onNavigateToPrintArrangement?: (templateId: string) => void;
}

export const DieMaterialAndLayoutManager: React.FC<Props> = ({ onNavigateToPrintArrangement }) => {
  // 刀模素材相关状态
  const [groupedMaterials, setGroupedMaterials] = useState<GroupedMaterials>({});
  const [materialsLoading, setMaterialsLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; material: DieMaterial | null }>({
    show: false,
    material: null,
  });

  // 布局模版相关状态
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<LayoutTemplate | null>(null);

  // 排版成品相关状态
  const [arrangements, setArrangements] = useState<PrintArrangement[]>([]);
  const [arrangementsLoading, setArrangementsLoading] = useState(true);
  const [deleteArrangementConfirm, setDeleteArrangementConfirm] = useState<{ show: boolean; arrangement: PrintArrangement | null }>({
    show: false,
    arrangement: null,
  });

  // 加载刀模素材数据
  const loadMaterials = async () => {
    setMaterialsLoading(true);
    try {
      const response = await apiService.getDieMaterials({ grouped: true });
      if (response.success && response.data) {
        setGroupedMaterials(response.data);
        setExpandedGroups(new Set(Object.keys(response.data)));
      }
    } catch (error) {
      console.error('加载刀模素材列表失败:', error);
    } finally {
      setMaterialsLoading(false);
    }
  };

  // 加载布局模版
  const loadTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const response = await apiService.getLayoutTemplates();
      if (response.success && response.data) {
        setTemplates(response.data);
      }
    } catch (error) {
      console.error('加载布局模版列表失败:', error);
    } finally {
      setTemplatesLoading(false);
    }
  };

  // 加载排版成品
  const loadArrangements = async () => {
    setArrangementsLoading(true);
    try {
      const response = await apiService.getPrintArrangements();
      if (response.success && response.data) {
        setArrangements(response.data);
      }
    } catch (error) {
      console.error('加载排版成品列表失败:', error);
    } finally {
      setArrangementsLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
    loadTemplates();
    loadArrangements();
  }, []);

  // 监听打印素材创建事件
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

  // 删除刀模素材
  const handleDeleteClick = (material: DieMaterial) => {
    setDeleteConfirm({ show: true, material });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm.material) return;

    try {
      const response = await apiService.deleteDieMaterial(deleteConfirm.material.id);
      if (response.success) {
        await loadMaterials();
      }
    } catch (error) {
      console.error('删除素材失败:', error);
    } finally {
      setDeleteConfirm({ show: false, material: null });
    }
  };

  // 下载刀模素材
  // 删除模版
  const handleDeleteTemplate = async (template: LayoutTemplate) => {
    try {
      const response = await apiService.deleteLayoutTemplate(template.id);
      if (response.success) {
        await loadTemplates();
        setSelectedTemplate(null);
      }
    } catch (error) {
      console.error('删除模版失败:', error);
    }
  };

  // 删除排版成品
  const handleDeleteArrangement = (arrangement: PrintArrangement) => {
    setDeleteArrangementConfirm({ show: true, arrangement });
  };

  const confirmDeleteArrangement = async () => {
    if (!deleteArrangementConfirm.arrangement) return;

    try {
      const response = await apiService.deletePrintArrangement(deleteArrangementConfirm.arrangement.id);
      if (response.success) {
        await loadArrangements();
      }
    } catch (error) {
      console.error('删除排版成品失败:', error);
    } finally {
      setDeleteArrangementConfirm({ show: false, arrangement: null });
    }
  };

  // 使用模板
  const handleUseTemplate = (templateId: string) => {
    if (onNavigateToPrintArrangement) {
      onNavigateToPrintArrangement(templateId);
    } else {
      alert('跳转功能未启用');
    }
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">刀模素材与排版管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理刀模素材与布局模版
          </p>
        </div>
      </div>

      {/* 三列布局 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 第1列：刀模素材管理 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">刀模素材</h3>

          {materialsLoading ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[800px] overflow-y-auto">
              {Object.keys(groupedMaterials).length === 0 ? (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <Image className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    还没有生成素材
                  </h3>
                  <p className="text-gray-500 text-sm">
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
                      className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors flex items-center justify-between"
                      onClick={() => toggleGroup(elementId)}
                    >
                      <div className="flex items-center space-x-2">
                        <div className="text-gray-500">
                          {expandedGroups.has(elementId) ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900 text-sm">{group.elementName}</h3>
                          <div className="text-xs text-gray-600 mt-0.5">
                            {group.cutSize.width}×{group.cutSize.height}cm | {group.materials.length}个
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 素材网格 */}
                    {expandedGroups.has(elementId) && (
                      <div className="p-2 grid grid-cols-3 gap-1.5">
                        {group.materials.map((material) => (
                          <div
                            key={material.id}
                            className="relative group aspect-square overflow-hidden rounded-lg border border-gray-200 bg-white"
                          >
                            {/* 素材预览 */}
                            <div className="absolute inset-0 flex items-center justify-center p-2">
                              <img
                                src={apiService.getDieMaterialUrl(material.id)}
                                alt={material.fileName}
                                className="max-w-full max-h-full object-contain"
                              />
                            </div>

                            {/* 操作按钮（悬停显示） */}
                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteClick(material);
                                }}
                                className="p-2 bg-white rounded-full hover:bg-red-50 transition-colors"
                                title="删除"
                              >
                                <Trash2 className="w-3.5 h-3.5 text-red-600" />
                              </button>
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
        </div>

        {/* 第2列：布局模版 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">布局模版</h3>

          {templatesLoading ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[800px] overflow-y-auto">
              {templates.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center">
                  <Layout className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    还没有布局模版
                  </h3>
                  <p className="text-gray-500 text-sm mb-6">
                    上传 PSD 文件创建布局模版
                  </p>
                  {/* PSD 上传组件 - 居中显示 */}
                  <LayoutTemplateUpload onUploadSuccess={loadTemplates} />
                </div>
              ) : (
                <>
                  {/* PSD 上传组件 - 模板列表顶部 */}
                  <LayoutTemplateUpload onUploadSuccess={loadTemplates} />
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => setSelectedTemplate(template)}
                    >
                      {/* 预览图 */}
                      <div className="aspect-[4/3] bg-gray-100 flex items-center justify-center">
                        <img
                          src={template.previewImage}
                          alt={template.name}
                          className="w-full h-full object-contain"
                        />
                      </div>

                      {/* 信息 */}
                      <div className="p-3">
                        <h4 className="font-medium text-gray-900 text-sm truncate">{template.name}</h4>
                        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                          <span>{template.paperSize} {template.paperOrientation === 'landscape' ? '横向' : '纵向'}</span>
                          <span>{template.elements.length} 个元素</span>
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {new Date(template.createdAt).toLocaleDateString('zh-CN')}
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        {/* 第3列：排版成品 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">排版成品</h3>

          {arrangementsLoading ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[800px] overflow-y-auto">
              {arrangements.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center">
                  <FileText className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    还没有排版成品
                  </h3>
                  <p className="text-gray-500 text-sm">
                    前往打印排版编辑器保存排版成品
                  </p>
                </div>
              ) : (
                arrangements.map((arrangement) => (
                  <div
                    key={arrangement.id}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
                  >
                    {/* 预览图 */}
                    {arrangement.previewFileName && (
                      <div className="aspect-[4/3] bg-gray-100 flex items-center justify-center">
                        <img
                          src={apiService.getPrintArrangementPreviewUrl(arrangement.id)}
                          alt={arrangement.name}
                          className="w-full h-full object-contain"
                        />
                      </div>
                    )}

                    {/* 信息与操作 */}
                    <div className="p-3">
                      <h4 className="font-medium text-gray-900 text-sm truncate">{arrangement.name}</h4>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(arrangement.createdAt).toLocaleDateString('zh-CN', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>

                      {/* 操作按钮 */}
                      <div className="flex gap-2 mt-3">
                        <a
                          href={apiService.getPrintArrangementDownloadUrl(arrangement.id)}
                          download
                          className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-primary-600 text-white text-xs font-medium rounded hover:bg-primary-700 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          下载PSD
                        </a>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteArrangement(arrangement);
                          }}
                          className="px-3 py-1.5 bg-red-50 text-red-600 text-xs font-medium rounded hover:bg-red-100 transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

      </div>

      {/* 删除刀模素材确认对话框 */}
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

      {/* 删除排版成品确认对话框 */}
      {deleteArrangementConfirm.show && deleteArrangementConfirm.arrangement && (
        <ConfirmDialog
          isOpen={deleteArrangementConfirm.show}
          title="删除排版成品"
          message={`确定要删除排版成品"${deleteArrangementConfirm.arrangement.name}"吗？此操作无法恢复。`}
          confirmText="删除"
          cancelText="取消"
          onConfirm={confirmDeleteArrangement}
          onCancel={() => setDeleteArrangementConfirm({ show: false, arrangement: null })}
          type="danger"
        />
      )}

      {/* 布局模版详情对话框 */}
      {selectedTemplate && (
        <TemplateDetailDialog
          isOpen={true}
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onDelete={handleDeleteTemplate}
          onUseTemplate={handleUseTemplate}
        />
      )}

    </div>
  );
};
