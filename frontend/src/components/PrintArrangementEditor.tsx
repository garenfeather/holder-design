import React, { useState, useEffect, useRef } from 'react';
import { X, ZoomIn, ZoomOut } from 'lucide-react';
import { LayoutTemplate } from '../types/index.ts';
import { apiService } from '../services/api.ts';

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

interface Props {
  templateId: string | null;
  onClose: () => void;
}

export const PrintArrangementEditor: React.FC<Props> = ({ templateId, onClose }) => {
  const [template, setTemplate] = useState<LayoutTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [materialMappings, setMaterialMappings] = useState<Map<string, string>>(new Map());
  const [availableMaterials, setAvailableMaterials] = useState<DieMaterial[]>([]);
  const [materialCache, setMaterialCache] = useState<Map<string, DieMaterial>>(new Map()); // 缓存所有素材
  const [scale, setScale] = useState(1);

  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const canvasImgRef = useRef<HTMLImageElement>(null);

  // 加载模板数据
  useEffect(() => {
    if (!templateId) {
      setLoading(false);
      return;
    }

    const loadTemplate = async () => {
      setLoading(true);
      try {
        const response = await apiService.getLayoutTemplate(templateId);
        if (response.success && response.data) {
          setTemplate(response.data);
        }
      } catch (error) {
        console.error('加载模板失败:', error);
        alert('加载模板失败');
        onClose();
      } finally {
        setLoading(false);
      }
    };

    loadTemplate();
  }, [templateId]);

  // 加载选中元素的素材列表
  useEffect(() => {
    if (!selectedElementId || !template) {
      setAvailableMaterials([]);
      return;
    }

    const element = template.elements.find(e => e.id === selectedElementId);
    if (!element) {
      setAvailableMaterials([]);
      return;
    }

    const loadMaterials = async () => {
      try {
        const response = await apiService.getDieMaterials({
          elementId: element.elementId
        });
        if (response.success && response.data) {
          // 如果返回的是分组数据，需要提取素材列表
          if (typeof response.data === 'object' && !Array.isArray(response.data)) {
            const group = Object.values(response.data as any)[0];
            setAvailableMaterials((group as any)?.materials || []);
          } else {
            setAvailableMaterials(response.data as DieMaterial[]);
          }
        }
      } catch (error) {
        console.error('加载素材列表失败:', error);
        setAvailableMaterials([]);
      }
    };

    loadMaterials();
  }, [selectedElementId, template]);

  // 画布点击处理
  const handleCanvasClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!template || !canvasImgRef.current || !canvasContainerRef.current) return;

    const img = canvasImgRef.current;
    const rect = img.getBoundingClientRect();

    // 计算点击位置（相对于图片）
    const clickX = (event.clientX - rect.left) / scale;
    const clickY = (event.clientY - rect.top) / scale;

    // 计算图片显示尺寸与实际画布尺寸的比例
    const canvasSize = template.canvasSize;
    if (!canvasSize) return;

    const displayScale = img.clientWidth / scale / canvasSize.width;

    // 查找点击的元素
    for (const element of template.elements) {
      const x = element.position.x * displayScale;
      const y = element.position.y * displayScale;
      let w = (element.cutSize.width * 10) * displayScale; // cm -> mm -> px
      let h = (element.cutSize.height * 10) * displayScale;

      // 考虑旋转
      if (element.rotation === 90) {
        [w, h] = [h, w];
      }

      if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h) {
        setSelectedElementId(element.id);
        return;
      }
    }

    // 如果没有点击到任何元素，取消选择
    setSelectedElementId(null);
  };

  // 滚轮缩放
  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const delta = event.deltaY > 0 ? 0.9 : 1.1;
    setScale(prev => Math.max(0.5, Math.min(3, prev * delta)));
  };

  // 选择素材
  const handleSelectMaterial = (materialId: string) => {
    if (!selectedElementId) return;

    // 缓存素材信息
    const material = availableMaterials.find(m => m.id === materialId);
    if (material) {
      const newCache = new Map(materialCache);
      newCache.set(materialId, material);
      setMaterialCache(newCache);
    }

    const newMappings = new Map(materialMappings);
    newMappings.set(selectedElementId, materialId);
    setMaterialMappings(newMappings);
  };

  // 清空当前选择
  const handleClearSelection = () => {
    if (!selectedElementId) return;

    const newMappings = new Map(materialMappings);
    newMappings.delete(selectedElementId);
    setMaterialMappings(newMappings);
  };

  // 缩放控制
  const handleZoomIn = () => {
    setScale(prev => Math.min(3, prev * 1.2));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(0.5, prev / 1.2));
  };

  const handleResetZoom = () => {
    setScale(1);
  };

  // 保存
  const handleSave = async () => {
    if (!template) return;

    const name = prompt('请输入打印素材名称');
    if (!name) return;

    // 转换materialMappings为API格式
    const mappings = Array.from(materialMappings.entries()).map(
      ([layoutElementId, materialId]) => ({
        layoutElementId,
        materialId
      })
    );

    try {
      const response = await apiService.createPrintMaterial({
        name,
        templateId: template.id,
        materialMappings: mappings
      });

      if (response.success) {
        alert('打印素材创建成功！');
        onClose();
      } else {
        alert(`保存失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败: ' + (error instanceof Error ? error.message : String(error)));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-gray-600">请先选择一个布局模板</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            返回
          </button>
        </div>
      </div>
    );
  }

  const selectedElement = selectedElementId
    ? template.elements.find(e => e.id === selectedElementId)
    : null;

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">排版打印</h2>
          <p className="text-sm text-gray-500 mt-1">模板: {template.name}</p>
        </div>

        <div className="flex items-center gap-4">
          {/* 缩放控制 */}
          <div className="flex items-center gap-2 border rounded-lg px-3 py-1">
            <button
              onClick={handleZoomOut}
              className="p-1 hover:bg-gray-100 rounded"
              title="缩小"
            >
              <ZoomOut size={18} />
            </button>
            <span className="text-sm text-gray-600 min-w-[60px] text-center">
              {(scale * 100).toFixed(0)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="p-1 hover:bg-gray-100 rounded"
              title="放大"
            >
              <ZoomIn size={18} />
            </button>
            <button
              onClick={handleResetZoom}
              className="text-xs text-blue-600 hover:underline"
            >
              重置
            </button>
          </div>

          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            title="关闭"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左列：素材选择 */}
        <div className="w-80 bg-white border-r overflow-y-auto">
          <div className="p-4">
            <h3 className="font-semibold text-gray-900 mb-2">素材选择</h3>

            {selectedElement ? (
              <div className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm font-medium text-blue-900">
                    当前选中: {selectedElement.elementName}
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    {selectedElement.cutSize.width} × {selectedElement.cutSize.height} cm
                  </p>
                </div>

                {availableMaterials.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 text-sm">
                    该元素还没有素材
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      {availableMaterials.map((material) => (
                        <div
                          key={material.id}
                          className={`
                            cursor-pointer border-2 rounded-lg overflow-hidden
                            transition-all hover:shadow-md
                            ${
                              materialMappings.get(selectedElementId) === material.id
                                ? 'border-blue-500 ring-2 ring-blue-200'
                                : 'border-gray-300 hover:border-blue-300'
                            }
                          `}
                          onClick={() => handleSelectMaterial(material.id)}
                        >
                          <div className="aspect-square bg-gray-100 flex items-center justify-center p-2">
                            <img
                              src={apiService.getDieMaterialUrl(material.id)}
                              alt={material.fileName}
                              className="max-w-full max-h-full object-contain"
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={handleClearSelection}
                      className="w-full px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      清空当前选择
                    </button>
                  </>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500 text-sm">
                <p>请点击右侧画布上的元素</p>
                <p className="mt-1">选择要填充的位置</p>
              </div>
            )}
          </div>
        </div>

        {/* 右列：排版画布 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto p-6">
            <div
              ref={canvasContainerRef}
              className="relative inline-block"
              style={{
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
                cursor: 'crosshair'
              }}
              onClick={handleCanvasClick}
              onWheel={handleWheel}
            >
              {/* 底层：模板预览图 */}
              <img
                ref={canvasImgRef}
                src={template.previewImage}
                alt="画布"
                className="block"
                style={{ pointerEvents: 'none' }}
              />

              {/* 叠加层：已填充的素材 */}
              {template.canvasSize && template.elements.map((element) => {
                const materialId = materialMappings.get(element.id);
                if (!materialId) return null;

                // 优先从缓存中获取素材，如果没有再从当前列表中查找
                let material = materialCache.get(materialId);
                if (!material) {
                  material = availableMaterials.find(m => m.id === materialId);
                }
                if (!material) {
                  return null; // 找不到素材，跳过
                }

                const imgElement = canvasImgRef.current;
                if (!imgElement) return null;

                const displayScale = imgElement.clientWidth / template.canvasSize.width;

                const baseWidth = (element.cutSize.width * 10) * displayScale; // cm -> mm -> px
                const baseHeight = (element.cutSize.height * 10) * displayScale;
                let displayWidth = baseWidth;
                let displayHeight = baseHeight;

                if (element.rotation === 90) {
                  [displayWidth, displayHeight] = [displayHeight, displayWidth];
                }

                // 素材尺寸
                const materialW = material.cutSize.width; // cm
                const materialH = material.cutSize.height; // cm
                // 元素尺寸
                const elementW = element.cutSize.width; // cm
                const elementH = element.cutSize.height; // cm

                // 判断素材是否需要旋转：素材a×b，元素b×a
                const needRotation = (
                  Math.abs(materialW - elementH) < 0.1 &&
                  Math.abs(materialH - elementW) < 0.1
                );

                const slotRotation = element.rotation ?? 0;
                const materialRotation = needRotation ? 90 : 0;
                const totalRotation = (slotRotation + materialRotation) % 360;
                const hasOddRotation = Math.abs(totalRotation) % 180 !== 0;

                return (
                  <div
                    key={element.id}
                    className={`
                      absolute overflow-hidden
                      ${
                        selectedElementId === element.id
                          ? 'ring-4 ring-blue-500'
                          : 'ring-2 ring-green-500'
                      }
                    `}
                    style={{
                      left: `${element.position.x * displayScale}px`,
                      top: `${element.position.y * displayScale}px`,
                      width: `${displayWidth}px`,
                      height: `${displayHeight}px`
                    }}
                  >
                    {material && (
                      <img
                        src={apiService.getDieMaterialUrl(material.id)}
                        alt=""
                        className="absolute object-cover opacity-80"
                        style={{
                          width: hasOddRotation ? `${displayHeight}px` : '100%',
                          height: hasOddRotation ? `${displayWidth}px` : '100%',
                          top: '50%',
                          left: '50%',
                          transform: `translate(-50%, -50%) rotate(${totalRotation}deg)`,
                          transformOrigin: 'center center'
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 底部操作栏 */}
          <div className="bg-white border-t px-6 py-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              已填充: {materialMappings.size} / {template.elements.length}
            </div>

            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                保存为打印素材
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
