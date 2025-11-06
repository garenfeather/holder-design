import React, { useState, useEffect } from 'react';
import { Image, Download, Trash2, Eye, ChevronDown, ChevronRight, FileText, Layout, FileImage } from 'lucide-react';
import { apiService } from '../services/api.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { ResultDetailModal } from './ResultDetailModal.tsx';
import { TemplateDetailDialog } from './TemplateDetailDialog.tsx';
import { PrintMaterialDetailDialog } from './PrintMaterialDetailDialog.tsx';
import { LayoutTemplate, PrintMaterial } from '../types/index.ts';

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

interface DieMaterialAndLayoutManagerProps {
  onUseTemplate?: (templateId: string) => void;
  onPrintMaterialCreated?: () => void;
}

export const DieMaterialAndLayoutManager: React.FC<DieMaterialAndLayoutManagerProps> = ({
  onUseTemplate,
  onPrintMaterialCreated,
}) => {
  // 刀模素材相关状态
  const [groupedMaterials, setGroupedMaterials] = useState<GroupedMaterials>({});
  const [materialsLoading, setMaterialsLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; material: DieMaterial | null }>({
    show: false,
    material: null,
  });
  const [previewMaterial, setPreviewMaterial] = useState<DieMaterial | null>(null);

  // 布局模版相关状态
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<LayoutTemplate | null>(null);
  const [deleteTemplateConfirm, setDeleteTemplateConfirm] = useState<{ show: boolean; template: LayoutTemplate | null }>({
    show: false,
    template: null,
  });

  // 打印素材相关状态
  const [printMaterials, setPrintMaterials] = useState<PrintMaterial[]>([]);
  const [printMaterialsLoading, setPrintMaterialsLoading] = useState(true);
  const [selectedPrintMaterial, setSelectedPrintMaterial] = useState<PrintMaterial | null>(null);
  const [deletePrintMaterialConfirm, setDeletePrintMaterialConfirm] = useState<{ show: boolean; printMaterial: PrintMaterial | null }>({
    show: false,
    printMaterial: null,
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

  // 加载打印素材
  const loadPrintMaterials = async () => {
    setPrintMaterialsLoading(true);
    try {
      const response = await apiService.getPrintMaterials();
      if (response.success && response.data) {
        setPrintMaterials(response.data);
      }
    } catch (error) {
      console.error('加载打印素材列表失败:', error);
    } finally {
      setPrintMaterialsLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
    loadTemplates();
    loadPrintMaterials();
  }, []);

  // 监听打印素材创建事件
  useEffect(() => {
    if (onPrintMaterialCreated) {
      loadPrintMaterials();
    }
  }, [onPrintMaterialCreated]);

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
  const handleDownload = (material: DieMaterial) => {
    const url = apiService.getDieMaterialUrl(material.id);
    const link = document.createElement('a');
    link.href = url;
    link.download = material.fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 预览刀模素材
  const handlePreview = (material: DieMaterial) => {
    setPreviewMaterial(material);
  };

  // 删除模版
  const handleDeleteTemplate = (template: LayoutTemplate) => {
    setDeleteTemplateConfirm({ show: true, template });
  };

  const confirmDeleteTemplate = async () => {
    if (!deleteTemplateConfirm.template) return;

    try {
      const response = await apiService.deleteLayoutTemplate(deleteTemplateConfirm.template.id);
      if (response.success) {
        await loadTemplates();
      }
    } catch (error) {
      console.error('删除模版失败:', error);
    } finally {
      setDeleteTemplateConfirm({ show: false, template: null });
      setSelectedTemplate(null);
    }
  };

  // 使用模版
  const handleUseTemplate = (templateId: string) => {
    if (onUseTemplate) {
      onUseTemplate(templateId);
    }
    setSelectedTemplate(null);
  };

  // 删除打印素材
  const handleDeletePrintMaterial = (printMaterial: PrintMaterial) => {
    setDeletePrintMaterialConfirm({ show: true, printMaterial });
  };

  const confirmDeletePrintMaterial = async () => {
    if (!deletePrintMaterialConfirm.printMaterial) return;

    try {
      const response = await apiService.deletePrintMaterial(deletePrintMaterialConfirm.printMaterial.id);
      if (response.success) {
        await loadPrintMaterials();
      }
    } catch (error) {
      console.error('删除打印素材失败:', error);
    } finally {
      setDeletePrintMaterialConfirm({ show: false, printMaterial: null });
      setSelectedPrintMaterial(null);
    }
  };

  // 下载打印素材PDF
  const handleDownloadPrintMaterialPDF = (printMaterialId: string) => {
    const url = apiService.getPrintMaterialPdfUrl(printMaterialId);
    const link = document.createElement('a');
    link.href = url;
    link.download = `print_material_${printMaterialId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">刀模素材与排版管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理刀模素材、布局模版和打印素材
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
                      <div className="p-2 grid grid-cols-2 gap-2">
                        {group.materials.map((material) => (
                          <div
                            key={material.id}
                            className="relative group bg-gray-50 rounded-lg overflow-hidden border border-gray-200"
                          >
                            {/* 素材预览 */}
                            <div className="aspect-square bg-gray-200 flex items-center justify-center">
                              <img
                                src={apiService.getDieMaterialUrl(material.id)}
                                alt={material.fileName}
                                className="w-full h-full object-contain"
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
                                  <Eye className="w-3.5 h-3.5 text-gray-700" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownload(material);
                                  }}
                                  className="p-1.5 bg-white rounded hover:bg-gray-100 transition-colors"
                                  title="下载"
                                >
                                  <Download className="w-3.5 h-3.5 text-gray-700" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteClick(material);
                                  }}
                                  className="p-1.5 bg-white rounded hover:bg-red-50 transition-colors"
                                  title="删除"
                                >
                                  <Trash2 className="w-3.5 h-3.5 text-red-600" />
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
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <Layout className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    还没有布局模版
                  </h3>
                  <p className="text-gray-500 text-sm">
                    前往打印排版功能创建布局模版
                  </p>
                </div>
              ) : (
                templates.map((template) => (
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
                ))
              )}
            </div>
          )}
        </div>

        {/* 第3列：打印素材 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">打印素材</h3>

          {printMaterialsLoading ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[800px] overflow-y-auto">
              {printMaterials.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <FileImage className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    还没有打印素材
                  </h3>
                  <p className="text-gray-500 text-sm">
                    使用布局模版填充素材后生成打印PDF
                  </p>
                </div>
              ) : (
                printMaterials.map((printMaterial) => (
                  <div
                    key={printMaterial.id}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelectedPrintMaterial(printMaterial)}
                  >
                    {/* 预览图 */}
                    <div className="aspect-[4/3] bg-gray-100 flex items-center justify-center">
                      <img
                        src={printMaterial.previewImage}
                        alt={printMaterial.name}
                        className="w-full h-full object-contain"
                      />
                    </div>

                    {/* 信息 */}
                    <div className="p-3">
                      <h4 className="font-medium text-gray-900 text-sm truncate">{printMaterial.name}</h4>
                      <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                        <span>模版: {printMaterial.templateName}</span>
                      </div>
                      <div className="flex items-center justify-between mt-1 text-xs text-gray-400">
                        <span>{formatFileSize(printMaterial.fileSize)}</span>
                        <span>{new Date(printMaterial.createdAt).toLocaleDateString('zh-CN')}</span>
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

      {/* 删除模版确认对话框 */}
      {deleteTemplateConfirm.show && deleteTemplateConfirm.template && (
        <ConfirmDialog
          isOpen={deleteTemplateConfirm.show}
          title="删除布局模版"
          message={`确定要删除模版"${deleteTemplateConfirm.template.name}"吗？此操作无法恢复。`}
          confirmText="删除"
          cancelText="取消"
          onConfirm={confirmDeleteTemplate}
          onCancel={() => setDeleteTemplateConfirm({ show: false, template: null })}
          type="danger"
        />
      )}

      {/* 删除打印素材确认对话框 */}
      {deletePrintMaterialConfirm.show && deletePrintMaterialConfirm.printMaterial && (
        <ConfirmDialog
          isOpen={deletePrintMaterialConfirm.show}
          title="删除打印素材"
          message={`确定要删除打印素材"${deletePrintMaterialConfirm.printMaterial.name}"吗？此操作无法恢复。`}
          confirmText="删除"
          cancelText="取消"
          onConfirm={confirmDeletePrintMaterial}
          onCancel={() => setDeletePrintMaterialConfirm({ show: false, printMaterial: null })}
          type="danger"
        />
      )}

      {/* 刀模素材预览模态框 */}
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

      {/* 布局模版详情对话框 */}
      {selectedTemplate && (
        <TemplateDetailDialog
          isOpen={true}
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onUseTemplate={handleUseTemplate}
          onDelete={handleDeleteTemplate}
        />
      )}

      {/* 打印素材详情对话框 */}
      {selectedPrintMaterial && (
        <PrintMaterialDetailDialog
          isOpen={true}
          printMaterial={selectedPrintMaterial}
          onClose={() => setSelectedPrintMaterial(null)}
          onDownload={handleDownloadPrintMaterialPDF}
          onDelete={handleDeletePrintMaterial}
        />
      )}
    </div>
  );
};
