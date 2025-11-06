import React, { useState, useEffect } from 'react';
import { X, Download, Trash2 } from 'lucide-react';
import { PrintMaterial } from '../types/index.ts';
import { apiService } from '../services/api.ts';

interface PrintMaterialDetailDialogProps {
  isOpen: boolean;
  printMaterial: PrintMaterial | null;
  onClose: () => void;
  onDownload: (printMaterialId: string) => void;
  onDelete: (printMaterialId: string) => void;
}

interface MaterialInfo {
  materialId: string;
  fileName: string;
  elementName: string;
  count: number;
}

export const PrintMaterialDetailDialog: React.FC<PrintMaterialDetailDialogProps> = ({
  isOpen,
  printMaterial,
  onClose,
  onDownload,
  onDelete,
}) => {
  const [materialInfos, setMaterialInfos] = useState<MaterialInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && printMaterial) {
      loadMaterialDetails();
    }
  }, [isOpen, printMaterial]);

  const loadMaterialDetails = async () => {
    if (!printMaterial) return;

    setLoading(true);
    try {
      // 统计每个素材的使用次数
      const materialStats: { [key: string]: { materialId: string; elementId: string; count: number } } = {};

      printMaterial.materialMappings.forEach((mapping) => {
        const key = `${mapping.materialId}_${mapping.elementId}`;
        if (!materialStats[key]) {
          materialStats[key] = {
            materialId: mapping.materialId,
            elementId: mapping.elementId,
            count: 0,
          };
        }
        materialStats[key].count++;
      });

      // 获取素材和元素的详细信息
      const infos: MaterialInfo[] = [];
      for (const stat of Object.values(materialStats)) {
        try {
          // 获取元素信息
          const elementResponse = await apiService.getDieElements();
          const element = elementResponse.data?.find((e: any) => e.id === stat.elementId);

          // 获取素材信息
          const materialsResponse = await apiService.getDieMaterials({ elementId: stat.elementId });
          const material = materialsResponse.data?.find((m: any) => m.id === stat.materialId);

          infos.push({
            materialId: stat.materialId,
            fileName: material?.fileName || '未知素材',
            elementName: element?.name || '未知元素',
            count: stat.count,
          });
        } catch (error) {
          console.error('加载素材详情失败:', error);
          infos.push({
            materialId: stat.materialId,
            fileName: '加载失败',
            elementName: '加载失败',
            count: stat.count,
          });
        }
      }

      setMaterialInfos(infos);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  if (!isOpen || !printMaterial) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">打印素材详情</h2>
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
                  src={printMaterial.previewImage}
                  alt={printMaterial.name}
                  className="w-full h-auto"
                />
              </div>
            </div>

            {/* 右侧：信息和统计 */}
            <div className="space-y-6">
              {/* PDF信息 */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">PDF信息</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">名称：</span>
                    <span className="font-medium text-gray-900">{printMaterial.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">使用的模版：</span>
                    <span className="font-medium text-gray-900">{printMaterial.templateName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">文件大小：</span>
                    <span className="font-medium text-gray-900">{formatFileSize(printMaterial.fileSize)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">创建时间：</span>
                    <span className="font-medium text-gray-900">
                      {new Date(printMaterial.createdAt).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">素材总数：</span>
                    <span className="font-medium text-gray-900">{printMaterial.materialMappings.length}</span>
                  </div>
                </div>
              </div>

              {/* 素材映射 */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">素材映射</h3>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  {loading ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                      <p className="mt-2 text-sm text-gray-500">加载中...</p>
                    </div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium text-gray-700">元素名称</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-700">素材文件</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-700">数量</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {materialInfos.map((info, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-2">{info.elementName}</td>
                            <td className="px-4 py-2 text-gray-600 truncate" title={info.fileName}>
                              {info.fileName}
                            </td>
                            <td className="px-4 py-2 text-center font-medium">{info.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200">
          <button
            onClick={() => {
              if (window.confirm(`确定要删除打印素材"${printMaterial.name}"吗？`)) {
                onDelete(printMaterial.id);
              }
            }}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span>删除</span>
          </button>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              关闭
            </button>
            <button
              onClick={() => onDownload(printMaterial.id)}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>下载PDF</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
