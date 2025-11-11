import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
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

type FillMode = 'single' | 'overwrite-all' | 'overwrite-remaining';

export const PrintArrangementEditor: React.FC<Props> = ({ templateId, onClose }) => {
  const [template, setTemplate] = useState<LayoutTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [materialMappings, setMaterialMappings] = useState<Map<string, string>>(new Map());
  const [availableMaterials, setAvailableMaterials] = useState<DieMaterial[]>([]);
  const [materialCache, setMaterialCache] = useState<Map<string, DieMaterial>>(new Map()); // 缓存所有素材
  const [hoveredElementId, setHoveredElementId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [fillMode, setFillMode] = useState<FillMode>('single'); // 新增：填充模式
  const SLOT_OVERDRAW_PX = 2; // 覆盖底层描边，避免浮点取整带来的缝隙
  // 排版画布保持原尺寸显示（不再支持缩放）

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
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    // 计算图片显示尺寸与实际画布尺寸的比例
    const canvasSize = template.canvasSize;
    if (!canvasSize) return;

    const displayScale = img.clientWidth / canvasSize.width;

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

  // 选择素材
  const handleSelectMaterial = (materialId: string) => {
    if (!selectedElementId || !template) return;

    // 缓存素材信息
    const material = availableMaterials.find(m => m.id === materialId);
    if (material) {
      const newCache = new Map(materialCache);
      newCache.set(materialId, material);
      setMaterialCache(newCache);
    }

    const newMappings = new Map(materialMappings);

    // 根据填充模式执行不同的逻辑
    if (fillMode === 'single') {
      // 仅添加当前: 只在点击的位置添加素材
      newMappings.set(selectedElementId, materialId);
    } else {
      // 获取当前选中元素的 elementId
      const selectedElement = template.elements.find(e => e.id === selectedElementId);
      if (!selectedElement) return;

      const targetElementId = selectedElement.elementId;

      // 找到所有相同 elementId 的元素
      const sameElements = template.elements.filter(e => e.elementId === targetElementId);

      if (fillMode === 'overwrite-all') {
        // 覆盖所有: 将所有该元素类型的位置都替换成当前素材
        sameElements.forEach(element => {
          newMappings.set(element.id, materialId);
        });
      } else if (fillMode === 'overwrite-remaining') {
        // 覆盖剩余: 只将未填充的位置替换成当前素材
        sameElements.forEach(element => {
          if (!materialMappings.has(element.id)) {
            newMappings.set(element.id, materialId);
          }
        });
        // 当前点击的位置也要设置
        newMappings.set(selectedElementId, materialId);
      }
    }

    setMaterialMappings(newMappings);
  };

  // 清空当前选择
  const handleClearSelection = () => {
    if (!selectedElementId) return;

    const newMappings = new Map(materialMappings);
    newMappings.delete(selectedElementId);
    setMaterialMappings(newMappings);
  };

  // 保存排版成品
  const handleSaveArrangement = async () => {
    if (!template || materialMappings.size === 0) {
      alert('请至少放置一个素材后再保存');
      return;
    }

    setSaving(true);
    try {
      // 将 Map 转换为普通对象
      const mappingsObj: Record<string, string> = {};
      materialMappings.forEach((materialId, layoutElementId) => {
        mappingsObj[layoutElementId] = materialId;
      });

      const response = await apiService.createPrintArrangement(template.id, mappingsObj);
      if (response.success) {
        alert('排版成品保存成功！');
        onClose();
      } else {
        alert(`保存失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('保存排版成品失败:', error);
      alert('保存失败，请稍后重试');
    } finally {
      setSaving(false);
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
          {/* 填充模式切换 */}
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setFillMode('single')}
              className={`
                px-3 py-1.5 rounded text-sm font-medium transition-all
                ${fillMode === 'single'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }
              `}
              title="只在点击的位置添加素材"
            >
              仅添加当前
            </button>
            <button
              onClick={() => setFillMode('overwrite-all')}
              className={`
                px-3 py-1.5 rounded text-sm font-medium transition-all
                ${fillMode === 'overwrite-all'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }
              `}
              title="将所有相同元素的位置都覆盖为当前素材"
            >
              覆盖所有
            </button>
            <button
              onClick={() => setFillMode('overwrite-remaining')}
              className={`
                px-3 py-1.5 rounded text-sm font-medium transition-all
                ${fillMode === 'overwrite-remaining'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }
              `}
              title="将所有未填充的相同元素位置覆盖为当前素材"
            >
              覆盖剩下
            </button>
          </div>

          {/* 保存按钮 */}
          <button
            onClick={handleSaveArrangement}
            disabled={saving || materialMappings.size === 0}
            className={`
              px-6 py-2 rounded-lg font-medium transition-all
              ${materialMappings.size === 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : saving
                  ? 'bg-blue-400 text-white cursor-wait'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }
            `}
            title={materialMappings.size === 0 ? '请至少放置一个素材' : '保存排版成品'}
          >
            {saving ? '保存中...' : '保存排版'}
          </button>

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
                                ? 'border-blue-600 ring-2 ring-blue-200'
                                : 'border-gray-300 hover:border-blue-600'
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
              className="relative inline-block cursor-crosshair"
              onClick={handleCanvasClick}
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

                // 优先从缓存中获取素材，如果没有再从当前列表中查找
                let material = materialId ? materialCache.get(materialId) : undefined;
                if (materialId && !material) {
                  material = availableMaterials.find(m => m.id === materialId);
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

                let materialUrl: string | null = null;
                if (material) {
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
                  const normalizedRotation = ((totalRotation % 360) + 360) % 360;
                  materialUrl = apiService.getDieMaterialUrl(material.id, {
                    rotate: normalizedRotation
                  });
                }

                const isSelected = selectedElementId === element.id;
                const isHovered = hoveredElementId === element.id;
                const outline = 'none';
                const transform = isHovered ? 'scale(1.01)' : 'scale(1)';
                const shadow = (isSelected || isHovered)
                  ? `0 0 0 2px rgba(59, 130, 246, ${isSelected ? 0.7 : 0.4})`
                  : 'none';

                const adjustedLeft = (element.position.x * displayScale) - (SLOT_OVERDRAW_PX / 2);
                const adjustedTop = (element.position.y * displayScale) - (SLOT_OVERDRAW_PX / 2);
                const adjustedWidth = displayWidth + SLOT_OVERDRAW_PX;
                const adjustedHeight = displayHeight + SLOT_OVERDRAW_PX;

                return (
                  <div
                    key={element.id}
                    className="absolute overflow-hidden transition-all duration-200"
                    style={{
                      left: `${adjustedLeft}px`,
                      top: `${adjustedTop}px`,
                      width: `${adjustedWidth}px`,
                      height: `${adjustedHeight}px`,
                      outline,
                      outlineOffset: 0,
                      transform,
                      boxShadow: shadow,
                      backgroundColor: materialUrl ? '#fff' : 'transparent'
                    }}
                    onMouseEnter={() => setHoveredElementId(element.id)}
                    onMouseLeave={() =>
                      setHoveredElementId((current) => (current === element.id ? null : current))
                    }
                  >
                    {materialUrl && (
                      <img
                        src={materialUrl}
                        alt=""
                        className="absolute object-cover"
                        style={{
                          width: '100%',
                          height: '100%',
                          top: 0,
                          left: 0,
                          transform: 'none'
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
                关闭
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
