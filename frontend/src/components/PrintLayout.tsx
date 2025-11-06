import React, { useState, useEffect, useRef } from 'react';
import { Stage, Layer, Rect, Text as KonvaText, Image as KonvaImage, Transformer, Line } from 'react-konva';
import { FileText, Download, Save, Grid, Copy, ZoomIn, ZoomOut, Trash2, ChevronDown, ChevronRight, RotateCw, ArrowLeft, Image } from 'lucide-react';
import { apiService } from '../services/api.ts';
import { DieElement, LayoutElement, LayoutTemplate } from '../types/index.ts';
import { TemplateNameDialog } from './TemplateNameDialog.tsx';
import { MaterialSelectionDialog } from './MaterialSelectionDialog.tsx';
import Konva from 'konva';

type PaperSize = 'A3' | 'A4';
type PaperOrientation = 'landscape' | 'portrait';
type WorkMode = 'design' | 'fill';

interface CanvasElement {
  id: string; // 画布元素实例ID
  elementId: string; // 刀模元素ID
  elementName: string;
  cutSize: {
    width: number; // cm
    height: number; // cm
  };
  x: number; // mm
  y: number; // mm
  rotation: number; // 0, 90, 180, 270
}

interface MaterialImageCache {
  [materialId: string]: HTMLImageElement;
}

const PAPER_SIZES = {
  A3: { width: 420, height: 297 }, // mm (横向)
  A4: { width: 297, height: 210 }, // mm (横向)
};

const BLEED_MARGIN = 5; // mm
const SNAP_THRESHOLD = 5; // 吸附阈值 (px)
const MM_TO_PX = 2; // 屏幕显示比例: 1mm = 2px

interface PrintLayoutProps {
  loadTemplateId?: string | null;
  onTemplateLoaded?: () => void;
  onPrintMaterialCreated?: () => void;
}

export const PrintLayout: React.FC<PrintLayoutProps> = ({
  loadTemplateId,
  onTemplateLoaded,
  onPrintMaterialCreated,
}) => {
  // 基础设置
  const [mode, setMode] = useState<WorkMode>('design');
  const [paperSize, setPaperSize] = useState<PaperSize>('A4');
  const [paperOrientation, setPaperOrientation] = useState<PaperOrientation>('landscape');
  const [zoom, setZoom] = useState<number>(100);

  // 数据
  const [dieElements, setDieElements] = useState<DieElement[]>([]);
  const [canvasElements, setCanvasElements] = useState<CanvasElement[]>([]);
  const [loadedTemplate, setLoadedTemplate] = useState<LayoutTemplate | null>(null);
  const [materialAssignments, setMaterialAssignments] = useState<Record<string, string>>({});
  const [materialImageCache, setMaterialImageCache] = useState<MaterialImageCache>({});

  // UI 状态
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [snapLines, setSnapLines] = useState<{ x: number[]; y: number[] }>({ x: [], y: [] });
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // 对话框
  const [templateNameDialogOpen, setTemplateNameDialogOpen] = useState(false);
  const [materialSelectionDialogOpen, setMaterialSelectionDialogOpen] = useState(false);
  const [selectedElementForMaterial, setSelectedElementForMaterial] = useState<{
    elementId: string;
    elementName: string;
    layoutElementId: string;
  } | null>(null);

  // 素材分组数据 (fill模式使用)
  const [groupedMaterials, setGroupedMaterials] = useState<{
    [elementId: string]: {
      elementName: string;
      materials: any[];
    };
  }>({});

  const stageRef = useRef<Konva.Stage>(null);
  const layerRef = useRef<Konva.Layer>(null);
  const transformerRef = useRef<Konva.Transformer>(null);

  // 获取实际纸张尺寸（考虑方向）
  const basePaper = PAPER_SIZES[paperSize];
  const paper = paperOrientation === 'portrait'
    ? { width: basePaper.height, height: basePaper.width }
    : basePaper;

  const safeWidth = paper.width - BLEED_MARGIN * 2;
  const safeHeight = paper.height - BLEED_MARGIN * 2;

  // 画布尺寸(px)
  const stageWidth = paper.width * MM_TO_PX * (zoom / 100);
  const stageHeight = paper.height * MM_TO_PX * (zoom / 100);
  const scale = MM_TO_PX * (zoom / 100);

  // 加载刀模元素列表 (design模式)
  useEffect(() => {
    if (mode === 'design') {
      loadDieElements();
    }
  }, [mode]);

  // 加载模版 (从外部传入templateId)
  useEffect(() => {
    if (loadTemplateId) {
      loadTemplate(loadTemplateId);
    }
  }, [loadTemplateId]);

  // fill模式下，加载素材分组数据
  useEffect(() => {
    if (mode === 'fill' && loadedTemplate) {
      loadMaterialsForTemplate();
    }
  }, [mode, loadedTemplate]);

  const loadDieElements = async () => {
    setLoading(true);
    try {
      const response = await apiService.getDieElements();
      if (response.success && response.data) {
        setDieElements(response.data);
      }
    } catch (error) {
      console.error('加载刀模元素失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplate = async (templateId: string) => {
    setLoading(true);
    try {
      const response = await apiService.getLayoutTemplates();
      if (response.success && response.data) {
        const template = response.data.find((t: LayoutTemplate) => t.id === templateId);
        if (template) {
          // 载入模版
          setLoadedTemplate(template);
          setPaperSize(template.paperSize);
          setPaperOrientation(template.paperOrientation);

          // 生成画布元素
          const elements: CanvasElement[] = template.elements.map((el) => ({
            id: el.id,
            elementId: el.elementId,
            elementName: el.elementName,
            cutSize: el.cutSize,
            x: el.x,
            y: el.y,
            rotation: el.rotation,
          }));

          setCanvasElements(elements);
          setMode('fill');
          setMaterialAssignments({});

          if (onTemplateLoaded) {
            onTemplateLoaded();
          }
        }
      }
    } catch (error) {
      console.error('加载模版失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMaterialsForTemplate = async () => {
    if (!loadedTemplate) return;

    // 获取模版中用到的所有元素ID
    const elementIds = Array.from(new Set(loadedTemplate.elements.map(el => el.elementId)));

    const grouped: typeof groupedMaterials = {};

    for (const elementId of elementIds) {
      try {
        const response = await apiService.getDieMaterials({ elementId });
        if (response.success && response.data) {
          const element = loadedTemplate.elements.find(el => el.elementId === elementId);
          grouped[elementId] = {
            elementName: element?.elementName || '未知元素',
            materials: response.data,
          };
        }
      } catch (error) {
        console.error(`加载元素${elementId}的素材失败:`, error);
      }
    }

    setGroupedMaterials(grouped);
    setExpandedGroups(new Set(Object.keys(grouped)));
  };

  // 添加元素到画布 (design模式)
  const addElementToCanvas = (element: DieElement) => {
    const newElement: CanvasElement = {
      id: `canvas-${Date.now()}-${Math.random()}`,
      elementId: element.id,
      elementName: element.name,
      cutSize: {
        width: element.cutWidth,
        height: element.cutHeight,
      },
      x: BLEED_MARGIN + 10,
      y: BLEED_MARGIN + 10,
      rotation: 0,
    };
    setCanvasElements([...canvasElements, newElement]);
  };

  // 删除选中的元素
  const deleteSelectedElement = () => {
    if (selectedId) {
      setCanvasElements(canvasElements.filter(el => el.id !== selectedId));
      // 同时删除素材分配
      const newAssignments = { ...materialAssignments };
      delete newAssignments[selectedId];
      setMaterialAssignments(newAssignments);
      setSelectedId(null);
    }
  };

  // 处理键盘删除
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
        e.preventDefault();
        deleteSelectedElement();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedId, canvasElements]);

  // Transformer 选择
  useEffect(() => {
    if (selectedId && transformerRef.current && layerRef.current) {
      const selectedNode = layerRef.current.findOne(`#${selectedId}`);
      if (selectedNode) {
        transformerRef.current.nodes([selectedNode]);
        transformerRef.current.getLayer()?.batchDraw();
      }
    } else if (transformerRef.current) {
      transformerRef.current.nodes([]);
    }
  }, [selectedId]);

  // 吸附逻辑
  const getSnapLines = (skipId: string) => {
    const safeLeft = BLEED_MARGIN;
    const safeRight = paper.width - BLEED_MARGIN;
    const safeTop = BLEED_MARGIN;
    const safeBottom = paper.height - BLEED_MARGIN;

    const verticalLines = [safeLeft, safeRight, paper.width / 2];
    const horizontalLines = [safeTop, safeBottom, paper.height / 2];

    canvasElements.forEach(el => {
      if (el.id !== skipId) {
        const elWidth = (el.rotation === 90 || el.rotation === 270) ? el.cutSize.height * 10 : el.cutSize.width * 10;
        const elHeight = (el.rotation === 90 || el.rotation === 270) ? el.cutSize.width * 10 : el.cutSize.height * 10;
        verticalLines.push(el.x, el.x + elWidth);
        horizontalLines.push(el.y, el.y + elHeight);
      }
    });

    return { vertical: verticalLines, horizontal: horizontalLines };
  };

  const snapToLines = (pos: { x: number; y: number }, width: number, height: number, skipId: string) => {
    const { vertical, horizontal } = getSnapLines(skipId);
    const threshold = SNAP_THRESHOLD / ((zoom / 100) * MM_TO_PX);

    let snappedX = pos.x;
    let snappedY = pos.y;
    const foundSnapLines = { x: [] as number[], y: [] as number[] };

    for (const line of vertical) {
      if (Math.abs(pos.x - line) < threshold) {
        snappedX = line;
        foundSnapLines.x.push(line);
        break;
      }
    }

    if (foundSnapLines.x.length === 0) {
      for (const line of vertical) {
        if (Math.abs(pos.x + width - line) < threshold) {
          snappedX = line - width;
          foundSnapLines.x.push(line);
          break;
        }
      }
    }

    for (const line of horizontal) {
      if (Math.abs(pos.y - line) < threshold) {
        snappedY = line;
        foundSnapLines.y.push(line);
        break;
      }
    }

    if (foundSnapLines.y.length === 0) {
      for (const line of horizontal) {
        if (Math.abs(pos.y + height - line) < threshold) {
          snappedY = line - height;
          foundSnapLines.y.push(line);
          break;
        }
      }
    }

    return { x: snappedX, y: snappedY, snapLines: foundSnapLines };
  };

  // 保存为模版
  const handleSaveAsTemplate = () => {
    if (canvasElements.length === 0) {
      alert('画布上没有元素，无法保存模版');
      return;
    }
    setTemplateNameDialogOpen(true);
  };

  const handleTemplateSave = async (name: string) => {
    setTemplateNameDialogOpen(false);
    setLoading(true);

    try {
      // 生成布局元素数据
      const elements: LayoutElement[] = canvasElements.map((el) => ({
        id: el.id,
        elementId: el.elementId,
        elementName: el.elementName,
        cutSize: el.cutSize,
        x: el.x,
        y: el.y,
        rotation: el.rotation,
      }));

      // 调用API保存模版
      const response = await apiService.createLayoutTemplate({
        name,
        paperSize,
        paperOrientation,
        elements,
      });

      if (response.success) {
        alert('模版保存成功！');
        // 可以选择清空画布或保持
      } else {
        alert(`保存失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('保存模版失败:', error);
      alert('保存模版失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 返回设计模式
  const handleBackToDesign = () => {
    setMode('design');
    setLoadedTemplate(null);
    setMaterialAssignments({});
    setCanvasElements([]);
  };

  // 生成打印PDF
  const handleGeneratePrintPDF = async () => {
    if (!loadedTemplate) return;

    // 检查是否所有元素都已分配素材
    const allAssigned = canvasElements.every(el => materialAssignments[el.id]);
    if (!allAssigned) {
      alert('请为所有元素分配素材后再生成PDF');
      return;
    }

    setLoading(true);
    try {
      // 构造素材映射数据
      const materialMappings = canvasElements.map(el => ({
        layoutElementId: el.id,
        materialId: materialAssignments[el.id],
        elementId: el.elementId,
      }));

      // 调用API生成打印素材
      const response = await apiService.createPrintMaterial({
        name: `打印素材_${loadedTemplate.name}_${new Date().toLocaleDateString()}`,
        templateId: loadedTemplate.id,
        materialMappings,
      });

      if (response.success) {
        alert('打印PDF生成成功！');
        if (onPrintMaterialCreated) {
          onPrintMaterialCreated();
        }
      } else {
        alert(`生成失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('生成打印PDF失败:', error);
      alert('生成打印PDF失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 点击元素选择素材 (fill模式)
  const handleElementClickForMaterial = (element: CanvasElement) => {
    setSelectedElementForMaterial({
      elementId: element.elementId,
      elementName: element.elementName,
      layoutElementId: element.id,
    });
    setMaterialSelectionDialogOpen(true);
  };

  // 选择素材
  const handleMaterialSelect = (materialId: string, option: 'current' | 'all' | 'unassigned') => {
    setMaterialSelectionDialogOpen(false);
    if (!selectedElementForMaterial) return;

    const newAssignments = { ...materialAssignments };

    if (option === 'current') {
      // 仅填入当前元素
      newAssignments[selectedElementForMaterial.layoutElementId] = materialId;
    } else if (option === 'all') {
      // 所有同元素均填入
      canvasElements.forEach(el => {
        if (el.elementId === selectedElementForMaterial.elementId) {
          newAssignments[el.id] = materialId;
        }
      });
    } else if (option === 'unassigned') {
      // 尚未分配的同元素均填入
      canvasElements.forEach(el => {
        if (el.elementId === selectedElementForMaterial.elementId && !materialAssignments[el.id]) {
          newAssignments[el.id] = materialId;
        }
      });
    }

    setMaterialAssignments(newAssignments);

    // 预加载图片
    if (!materialImageCache[materialId]) {
      const img = new window.Image();
      img.crossOrigin = 'anonymous';
      img.src = apiService.getDieMaterialUrl(materialId);
      img.onload = () => {
        setMaterialImageCache(prev => ({ ...prev, [materialId]: img }));
      };
    }

    setSelectedElementForMaterial(null);
  };

  // 画布旋转
  const handleRotateCanvas = () => {
    const newOrientation = paperOrientation === 'landscape' ? 'portrait' : 'landscape';
    const oldPaper = paperOrientation === 'portrait'
      ? { width: basePaper.height, height: basePaper.width }
      : basePaper;

    const rotatedElements = canvasElements.map(el => {
      const elWidth = (el.rotation === 90 || el.rotation === 270) ? el.cutSize.height * 10 : el.cutSize.width * 10;
      const elHeight = (el.rotation === 90 || el.rotation === 270) ? el.cutSize.width * 10 : el.cutSize.height * 10;

      return {
        ...el,
        x: el.y,
        y: oldPaper.width - el.x - elWidth,
        rotation: (el.rotation + 90) % 360,
      };
    });

    setPaperOrientation(newOrientation);
    setCanvasElements(rotatedElements);
    setSelectedId(null);
  };

  const handleZoomIn = () => setZoom(Math.min(zoom + 10, 200));
  const handleZoomOut = () => setZoom(Math.max(zoom - 10, 50));
  const handleZoomReset = () => setZoom(100);

  const toggleGroup = (elementId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(elementId)) {
      newExpanded.delete(elementId);
    } else {
      newExpanded.add(elementId);
    }
    setExpandedGroups(newExpanded);
  };

  // 渲染画布元素
  const renderCanvasElement = (element: CanvasElement) => {
    const elWidth = (element.rotation === 90 || element.rotation === 270)
      ? element.cutSize.height * 10
      : element.cutSize.width * 10;
    const elHeight = (element.rotation === 90 || element.rotation === 270)
      ? element.cutSize.width * 10
      : element.cutSize.height * 10;

    const materialId = materialAssignments[element.id];
    const materialImage = materialId ? materialImageCache[materialId] : null;

    // fill模式且已分配素材：显示素材图片
    if (mode === 'fill' && materialImage) {
      return (
        <KonvaImage
          key={element.id}
          id={element.id}
          image={materialImage}
          x={element.x}
          y={element.y}
          width={elWidth}
          height={elHeight}
          rotation={element.rotation}
          scaleX={MM_TO_PX * (zoom / 100)}
          scaleY={MM_TO_PX * (zoom / 100)}
          draggable={mode === 'design'}
          onClick={() => {
            if (mode === 'fill') {
              handleElementClickForMaterial(element);
            } else {
              setSelectedId(element.id);
            }
          }}
          onTap={() => {
            if (mode === 'fill') {
              handleElementClickForMaterial(element);
            } else {
              setSelectedId(element.id);
            }
          }}
          onDragStart={() => setSelectedId(element.id)}
          onDragMove={(e) => handleDragMove(e, element)}
          onDragEnd={(e) => handleDragEnd(e, element, elWidth, elHeight)}
          dragBoundFunc={(pos) => getDragBound(pos, elWidth, elHeight)}
          onTransformEnd={(e) => handleTransformEnd(e, element)}
        />
      );
    }

    // design模式 或 fill模式未分配素材：显示蓝色边框 + 元素名称
    return (
      <React.Fragment key={element.id}>
        <Rect
          id={element.id}
          x={element.x}
          y={element.y}
          width={elWidth}
          height={elHeight}
          rotation={element.rotation}
          stroke="#3b82f6"
          strokeWidth={1}
          scaleX={MM_TO_PX * (zoom / 100)}
          scaleY={MM_TO_PX * (zoom / 100)}
          draggable={mode === 'design'}
          onClick={() => {
            if (mode === 'fill') {
              handleElementClickForMaterial(element);
            } else {
              setSelectedId(element.id);
            }
          }}
          onTap={() => {
            if (mode === 'fill') {
              handleElementClickForMaterial(element);
            } else {
              setSelectedId(element.id);
            }
          }}
          onDragStart={() => setSelectedId(element.id)}
          onDragMove={(e) => handleDragMove(e, element)}
          onDragEnd={(e) => handleDragEnd(e, element, elWidth, elHeight)}
          dragBoundFunc={(pos) => getDragBound(pos, elWidth, elHeight)}
          onTransformEnd={(e) => handleTransformEnd(e, element)}
        />
        <KonvaText
          text={element.elementName}
          x={element.x}
          y={element.y + elHeight / 2}
          width={elWidth}
          rotation={element.rotation}
          fill="#3b82f6"
          fontSize={10}
          align="center"
          verticalAlign="middle"
          scaleX={MM_TO_PX * (zoom / 100)}
          scaleY={MM_TO_PX * (zoom / 100)}
          listening={false}
        />
      </React.Fragment>
    );
  };

  const handleDragMove = (e: any, element: CanvasElement) => {
    const node = e.target;
    const pos = { x: node.x(), y: node.y() };
    const elWidth = (element.rotation === 90 || element.rotation === 270)
      ? element.cutSize.height * 10
      : element.cutSize.width * 10;
    const elHeight = (element.rotation === 90 || element.rotation === 270)
      ? element.cutSize.width * 10
      : element.cutSize.height * 10;
    const snapped = snapToLines(pos, elWidth, elHeight, element.id);
    node.position(snapped);
    setSnapLines(snapped.snapLines);
  };

  const handleDragEnd = (e: any, element: CanvasElement, elWidth: number, elHeight: number) => {
    const node = e.target;
    let x = node.x();
    let y = node.y();

    x = Math.max(BLEED_MARGIN, Math.min(x, paper.width - BLEED_MARGIN - elWidth));
    y = Math.max(BLEED_MARGIN, Math.min(y, paper.height - BLEED_MARGIN - elHeight));

    node.position({ x, y });

    const newElements = canvasElements.map(el =>
      el.id === element.id ? { ...el, x, y } : el
    );
    setCanvasElements(newElements);
    setSnapLines({ x: [], y: [] });
  };

  const getDragBound = (pos: { x: number; y: number }, elWidth: number, elHeight: number) => {
    return {
      x: Math.max(BLEED_MARGIN, Math.min(pos.x, paper.width - BLEED_MARGIN - elWidth)),
      y: Math.max(BLEED_MARGIN, Math.min(pos.y, paper.height - BLEED_MARGIN - elHeight))
    };
  };

  const handleTransformEnd = (e: any, element: CanvasElement) => {
    const node = e.target;
    let rotation = node.rotation();
    rotation = Math.round(rotation / 90) * 90;
    node.rotation(rotation);

    const elWidth = (rotation === 90 || rotation === 270)
      ? element.cutSize.height * 10
      : element.cutSize.width * 10;
    const elHeight = (rotation === 90 || rotation === 270)
      ? element.cutSize.width * 10
      : element.cutSize.height * 10;

    let x = node.x();
    let y = node.y();
    x = Math.max(BLEED_MARGIN, Math.min(x, paper.width - BLEED_MARGIN - elWidth));
    y = Math.max(BLEED_MARGIN, Math.min(y, paper.height - BLEED_MARGIN - elHeight));
    node.position({ x, y });

    const newElements = canvasElements.map(el =>
      el.id === element.id ? { ...el, x, y, rotation } : el
    );
    setCanvasElements(newElements);
  };

  // 检查是否所有元素都已分配素材
  const allAssigned = mode === 'fill' && canvasElements.every(el => materialAssignments[el.id]);

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'design' ? '元素布局设计' : '素材填充'}
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {mode === 'design'
              ? '将刀模元素排版到纸张上，保存为布局模版'
              : '为布局中的元素分配素材，生成打印PDF'}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {mode === 'design' ? (
            <button
              onClick={handleSaveAsTemplate}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <Save className="w-4 h-4" />
              <span>保存为模版</span>
            </button>
          ) : (
            <>
              <button
                onClick={handleBackToDesign}
                className="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>返回设计模式</span>
              </button>
              <button
                onClick={handleGeneratePrintPDF}
                disabled={!allAssigned}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                <span>生成打印PDF</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* 纸张设置 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center space-x-6">
          <span className="text-sm font-medium text-gray-700">纸张尺寸:</span>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                setPaperSize('A4');
                setCanvasElements([]);
                setSelectedId(null);
              }}
              disabled={mode === 'fill'}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                paperSize === 'A4'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${mode === 'fill' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              A4 (297×210mm)
            </button>
            <button
              onClick={() => {
                setPaperSize('A3');
                setCanvasElements([]);
                setSelectedId(null);
              }}
              disabled={mode === 'fill'}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                paperSize === 'A3'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${mode === 'fill' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              A3 (420×297mm)
            </button>
          </div>
          <div className="border-l border-gray-300 h-6 mx-2"></div>
          <span className="text-sm font-medium text-gray-700">纸张方向:</span>
          <button
            onClick={handleRotateCanvas}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors text-sm"
          >
            <RotateCw className="w-4 h-4" />
            <span>旋转90°</span>
          </button>
          <div className="text-sm text-gray-500">
            当前尺寸: {paper.width}×{paper.height}mm | 可排版区域: {safeWidth}×{safeHeight}mm
          </div>
        </div>
      </div>

      {/* 工具栏 */}
      {mode === 'design' && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center space-x-3">
            <span className="text-sm font-medium text-gray-700">快捷工具:</span>
            <button
              onClick={deleteSelectedElement}
              disabled={!selectedId}
              className="flex items-center space-x-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-4 h-4" />
              <span>删除</span>
            </button>
          </div>
        </div>
      )}

      {/* 主要工作区域 */}
      <div className="grid grid-cols-12 gap-6">
        {/* 左侧栏 */}
        <div className={`${mode === 'design' ? 'col-span-2' : 'col-span-3'} space-y-4`}>
          <div className="bg-white rounded-xl border border-gray-200 p-4 max-h-[700px] overflow-y-auto">
            <h3 className="font-semibold text-gray-900 mb-4">
              {mode === 'design' ? '刀模元素' : '可用素材'}
            </h3>

            {loading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                <p className="mt-2 text-gray-500 text-sm">加载中...</p>
              </div>
            ) : mode === 'design' ? (
              // design模式：显示元素列表
              dieElements.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">
                  <FileText className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  暂无刀模元素
                </div>
              ) : (
                <div className="space-y-2">
                  {dieElements.map((element) => (
                    <div
                      key={element.id}
                      onClick={() => addElementToCanvas(element)}
                      className="p-3 bg-gray-50 rounded-lg border border-gray-200 cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-all"
                    >
                      <div className="text-sm font-semibold text-gray-900">{element.name}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {element.cutWidth}×{element.cutHeight}cm
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              // fill模式：显示分组素材
              Object.keys(groupedMaterials).length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无可用素材
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(groupedMaterials).map(([elementId, group]) => (
                    <div key={elementId} className="border border-gray-200 rounded-lg overflow-hidden">
                      <div
                        className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors flex items-center justify-between"
                        onClick={() => toggleGroup(elementId)}
                      >
                        <div className="flex items-center space-x-2">
                          {expandedGroups.has(elementId) ? (
                            <ChevronDown className="w-4 h-4 text-gray-500" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                          )}
                          <div className="text-sm font-semibold text-gray-900">{group.elementName}</div>
                        </div>
                      </div>

                      {expandedGroups.has(elementId) && (
                        <div className="p-2 grid grid-cols-2 gap-2">
                          {group.materials.map((material: any) => (
                            <div
                              key={material.id}
                              className="relative group bg-gray-50 rounded-lg overflow-hidden border border-gray-200 cursor-pointer hover:border-primary-400 transition-all"
                              onClick={() => {
                                const element = canvasElements.find(el => el.elementId === elementId);
                                if (element) {
                                  setSelectedElementForMaterial({
                                    elementId: element.elementId,
                                    elementName: element.elementName,
                                    layoutElementId: element.id,
                                  });
                                  setMaterialSelectionDialogOpen(true);
                                }
                              }}
                            >
                              <div className="aspect-square bg-gray-200 flex items-center justify-center">
                                <img
                                  src={apiService.getDieMaterialUrl(material.id)}
                                  alt={material.fileName}
                                  className="w-full h-full object-contain"
                                />
                              </div>
                              <div className="p-1.5 text-xs text-gray-600 truncate bg-white">
                                {material.fileName}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </div>

        {/* 右侧：画布 */}
        <div className={`${mode === 'design' ? 'col-span-10' : 'col-span-9'}`}>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">排版画布</h3>

              <div className="flex items-center space-x-2">
                <button onClick={handleZoomOut} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button onClick={handleZoomReset} className="px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                  {zoom}%
                </button>
                <button onClick={handleZoomIn} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                  <ZoomIn className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="bg-gray-100 rounded-lg p-8 min-h-[600px] flex items-center justify-center overflow-auto">
              <Stage
                ref={stageRef}
                width={stageWidth}
                height={stageHeight}
                onClick={(e) => {
                  if (e.target === e.target.getStage()) {
                    setSelectedId(null);
                  }
                }}
                style={{ background: 'white', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
              >
                <Layer ref={layerRef}>
                  <Rect x={0} y={0} width={paper.width} height={paper.height} fill="white" scaleX={scale / MM_TO_PX} scaleY={scale / MM_TO_PX} />
                  <Rect x={BLEED_MARGIN} y={BLEED_MARGIN} width={safeWidth} height={safeHeight} stroke="#ef4444" strokeWidth={1} dash={[5, 5]} scaleX={scale / MM_TO_PX} scaleY={scale / MM_TO_PX} />

                  {snapLines.x.map((x, i) => (
                    <Line key={`snap-x-${i}`} points={[x, 0, x, paper.height]} stroke="#3b82f6" strokeWidth={1} dash={[4, 4]} scaleX={scale / MM_TO_PX} scaleY={scale / MM_TO_PX} />
                  ))}
                  {snapLines.y.map((y, i) => (
                    <Line key={`snap-y-${i}`} points={[0, y, paper.width, y]} stroke="#3b82f6" strokeWidth={1} dash={[4, 4]} scaleX={scale / MM_TO_PX} scaleY={scale / MM_TO_PX} />
                  ))}

                  {canvasElements.map(renderCanvasElement)}

                  {mode === 'design' && (
                    <Transformer
                      ref={transformerRef}
                      enabledAnchors={[]}
                      rotateEnabled={true}
                      borderEnabled={true}
                      borderStroke="#3b82f6"
                      borderStrokeWidth={2}
                      rotationSnaps={[0, 90, 180, 270]}
                      rotationSnapTolerance={45}
                    />
                  )}
                </Layer>
              </Stage>
            </div>

            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <div>
                {mode === 'design'
                  ? '提示: 点击左侧元素添加到画布 | 拖拽移动 | 旋转调整角度 | Delete键删除'
                  : `提示: 点击元素选择素材 | 已分配: ${Object.keys(materialAssignments).length} / ${canvasElements.length}`}
              </div>
              <div>
                已放置: {canvasElements.length} 个元素
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 对话框 */}
      <TemplateNameDialog
        isOpen={templateNameDialogOpen}
        onClose={() => setTemplateNameDialogOpen(false)}
        onSave={handleTemplateSave}
      />

      {selectedElementForMaterial && (
        <MaterialSelectionDialog
          isOpen={materialSelectionDialogOpen}
          elementId={selectedElementForMaterial.elementId}
          elementName={selectedElementForMaterial.elementName}
          currentLayoutElementId={selectedElementForMaterial.layoutElementId}
          onClose={() => {
            setMaterialSelectionDialogOpen(false);
            setSelectedElementForMaterial(null);
          }}
          onSelect={handleMaterialSelect}
        />
      )}
    </div>
  );
};
