import React, { useState, useRef, useEffect } from 'react';
import { X, Upload, Check, AlertTriangle, RotateCcw, Download, Eye, EyeOff, Crop, AlignCenter, ZoomIn, ZoomOut, RotateCw, Package } from 'lucide-react';
import { Template, GenerateResult, Component } from '../types/index.ts';
import { apiService, API_BASE_URL } from '../services/api.ts';

interface UseModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: Template | null;
  onGenerate?: (imageFile: File, template: Template) => void;
}

interface ImageTransform {
  x: number;      // 图片在编辑器中的X偏移
  y: number;      // 图片在编辑器中的Y偏移
  scale: number;  // 图片缩放比例
  rotation: number; // 图片旋转角度
}

export const UseModal: React.FC<UseModalProps> = ({
  isOpen,
  onClose,
  template,
  onGenerate
}) => {
  const [step, setStep] = useState<'upload' | 'edit' | 'component' | 'generate' | 'result'>('component');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [ratioCheck, setRatioCheck] = useState<{
    isMatch: boolean;
    userRatio: number;
    templateRatio: number;
  } | null>(null);
  const [imageTransform, setImageTransform] = useState<ImageTransform>({
    x: 0,
    y: 0,
    scale: 1,
    rotation: 0
  });
  const [forceResize, setForceResize] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [originalImageSize, setOriginalImageSize] = useState<{ width: number; height: number } | null>(null);
  const [editedPreview, setEditedPreview] = useState<string | null>(null);
  const [editedSize, setEditedSize] = useState<{ width: number; height: number } | null>(null);
  const [finalPreviewSize, setFinalPreviewSize] = useState<{ width: number; height: number } | null>(null);
  const [cutPreviewSize, setCutPreviewSize] = useState<{ width: number; height: number } | null>(null);
  const [componentPreviewSize, setComponentPreviewSize] = useState<{ width: number; height: number } | null>(null);
  const [showReferenceOverlay, setShowReferenceOverlay] = useState(false);
  const [showPreviewOverlay, setShowPreviewOverlay] = useState(false);
  const [selectedStrokeWidth, setSelectedStrokeWidth] = useState<number | null>(null);
  const [overlayOpacity, setOverlayOpacity] = useState<number>(100); // 0-100
  const [cropBoxSize, setCropBoxSize] = useState<{ width: number; height: number }>({ width: 300, height: 300 });
  const [imageDisplayInfo, setImageDisplayInfo] = useState<{ width: number; height: number; initialX: number; initialY: number } | null>(null);
  const [availableComponents, setAvailableComponents] = useState<Component[]>([]);
  const [selectedComponent, setSelectedComponent] = useState<Component | null>(null);
  const [componentsLoading, setComponentsLoading] = useState(false);
  // 组件选择区域宽度，严格贴合预览宽度
  const [componentSelectWidth, setComponentSelectWidth] = useState<number | null>(null);
  const componentSectionRef = useRef<HTMLDivElement>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      // 重置状态
      setStep('component');
      setSelectedImage(null);
      setImagePreview(null);
      setEditedPreview(null);
      setEditedSize(null);
      setRatioCheck(null);
      setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
      setForceResize(false);
      setIsProcessing(false);
      setGenerateResult(null);
      setUploadProgress(0);
      setOriginalImageSize(null);
      setShowReferenceOverlay(false);
      setShowPreviewOverlay(false);
      setAvailableComponents([]);
      setSelectedComponent(null);
      setComponentsLoading(false);
      setCropBoxSize({ width: 300, height: 300 });
      setImageDisplayInfo(null);
    }
  }, [isOpen]);

  // 释放编辑预览URL以避免内存泄漏
  useEffect(() => {
    return () => {
      if (editedPreview) URL.revokeObjectURL(editedPreview);
    };
  }, [editedPreview]);

  // 加载部件列表
  const loadComponents = async () => {
    if (!template) return;
    
    setComponentsLoading(true);
    try {
      const res = await apiService.getTemplateComponents(template.id);
      if (res.success && res.data) {
        setAvailableComponents(res.data);
        if (res.data.length === 0) {
          setStep(prev => (prev === 'component' ? 'upload' : prev));
        }
      } else {
        setAvailableComponents([]);
        setStep(prev => (prev === 'component' ? 'upload' : prev));
      }
    } catch (error) {
      console.error('Failed to load components:', error);
      setAvailableComponents([]);
      setStep(prev => (prev === 'component' ? 'upload' : prev));
    } finally {
      setComponentsLoading(false);
    }
  };

  // 当进入部件选择步骤时加载部件
  useEffect(() => {
    if (step === 'component' && template) {
      loadComponents();
    }
  }, [step, template]);

  // 计算部件选择区域的目标宽度：严格按预览宽度（依据viewport可用高度和view比例）
  useEffect(() => {
    if (!template?.viewLayer) return;
    const compute = () => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const aspect = (template.viewLayer!.width || 1) / (template.viewLayer!.height || 1);
      // 预估模态内可用高度（扣除头部/底部/内边距），取 60% 视口高度作为可用空间基准
      const usableH = Math.max(240, Math.min(vh * 0.6, vh - 240));
      const targetW = Math.min(vw - 64, Math.floor(usableH * aspect));
      setComponentSelectWidth(targetW);
    };
    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, [template?.id, step]);

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !template) return;

    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件');
      return;
    }

    setSelectedImage(file);
    
    // 创建预览
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setImagePreview(result);
      
      // 检查比例
      const img = new Image();
      img.onload = () => {
        checkImageRatio(img.width, img.height);
        setOriginalImageSize({ width: img.width, height: img.height });
        
        // 延迟计算，确保编辑器DOM已完全渲染
        setTimeout(() => {
          // 根据模板比例计算固定裁切框尺寸（占编辑器宽度80%）
          const targetAspectRatio = template?.viewLayer ? template.viewLayer.width / template.viewLayer.height : 1;
          const editorSize = getEditorSize();
          console.log('编辑器实际尺寸:', editorSize); // 调试信息
          
          // 基于编辑器宽度的80%来计算，而不是取宽高的最小值
          const maxCropWidth = editorSize.width * 0.8;
          const maxCropHeight = editorSize.height * 0.8;
          
          let cropBoxWidth, cropBoxHeight;
          if (targetAspectRatio > 1) {
            // 横向图片 - 优先使用宽度的80%
            cropBoxWidth = maxCropWidth;
            cropBoxHeight = maxCropWidth / targetAspectRatio;
            
            // 如果高度超出限制，则按高度调整
            if (cropBoxHeight > maxCropHeight) {
              cropBoxHeight = maxCropHeight;
              cropBoxWidth = maxCropHeight * targetAspectRatio;
            }
          } else {
            // 纵向图片 - 优先使用宽度的80%
            cropBoxWidth = maxCropWidth;
            cropBoxHeight = maxCropWidth / targetAspectRatio;
            
            // 如果高度超出限制，则按高度调整
            if (cropBoxHeight > maxCropHeight) {
              cropBoxHeight = maxCropHeight;
              cropBoxWidth = maxCropHeight * targetAspectRatio;
            }
          }
          
          console.log('计算的选框尺寸:', { width: cropBoxWidth, height: cropBoxHeight }); // 调试信息
          setCropBoxSize({ width: cropBoxWidth, height: cropBoxHeight });
          
          // 计算图片显示信息（适应动态编辑器）
          const displayHeight = editorSize.height * 0.8; // 编辑器高度的80%
          const displayWidth = (img.width / img.height) * displayHeight;
          const initialX = (editorSize.width - displayWidth) / 2;
          const initialY = (editorSize.height - displayHeight) / 2;
          
          setImageDisplayInfo({
            width: displayWidth,
            height: displayHeight,
            initialX,
            initialY
          });
          
          // 重置图片变换状态
          setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
        }, 100); // 100ms延迟，确保DOM渲染完成
      };
      img.src = result;
    };
    reader.readAsDataURL(file);
  };

  const checkImageRatio = (imageWidth: number, imageHeight: number) => {
    if (!template?.viewLayer) return;

    const userRatio = imageWidth / imageHeight;
    const templateRatio = template.viewLayer.width / template.viewLayer.height;
    const tolerance = 0.1; // 10% 容差
    
    const isMatch = Math.abs(userRatio - templateRatio) <= tolerance;
    
    setRatioCheck({
      isMatch,
      userRatio,
      templateRatio
    });

    if (isMatch) {
      setStep('generate');
    } else {
      setStep('edit');
    }
  };


  const getEditorSize = () => {
    if (!editorRef.current) return { width: 800, height: 500 }; // 默认尺寸
    const rect = editorRef.current.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  };

  const resetEdit = () => {
    setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
  };

  // 图片拖拽移动处理
  const handleImageMove = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX - imageTransform.x;
    const startY = e.clientY - imageTransform.y;

    const handleMouseMove = (e: MouseEvent) => {
      setImageTransform(prev => ({
        ...prev,
        x: e.clientX - startX,
        y: e.clientY - startY,
      }));
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // 图片缩放处理
  const handleImageScale = (e: React.MouseEvent, corner: 'tl' | 'tr' | 'bl' | 'br') => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!imageDisplayInfo) return;
    
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;
    const startScale = imageTransform.scale;
    const startX = imageTransform.x;
    const startY = imageTransform.y;
    
    // 计算图片中心点
    const imageCenterX = imageDisplayInfo.initialX + startX + (imageDisplayInfo.width * startScale) / 2;
    const imageCenterY = imageDisplayInfo.initialY + startY + (imageDisplayInfo.height * startScale) / 2;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startMouseX;
      const deltaY = e.clientY - startMouseY;
      
      // 根据角落计算缩放方向
      let scaleMultiplier = 1;
      switch (corner) {
        case 'tl': // 左上角：向左上拖拽放大
          scaleMultiplier = 1 + (-deltaX - deltaY) / 200;
          break;
        case 'tr': // 右上角：向右上拖拽放大
          scaleMultiplier = 1 + (deltaX - deltaY) / 200;
          break;
        case 'bl': // 左下角：向左下拖拽放大
          scaleMultiplier = 1 + (-deltaX + deltaY) / 200;
          break;
        case 'br': // 右下角：向右下拖拽放大
          scaleMultiplier = 1 + (deltaX + deltaY) / 200;
          break;
      }
      
      const newScale = Math.max(0.1, Math.min(5, startScale * scaleMultiplier));
      
      // 保持图片中心位置不变
      const newWidth = imageDisplayInfo.width * newScale;
      const newHeight = imageDisplayInfo.height * newScale;
      const newX = imageCenterX - imageDisplayInfo.initialX - newWidth / 2;
      const newY = imageCenterY - imageDisplayInfo.initialY - newHeight / 2;
      
      setImageTransform(prev => ({
        ...prev,
        scale: newScale,
        x: newX,
        y: newY,
      }));
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // 图片缩放处理
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(3, imageTransform.scale * scaleFactor));
    
    setImageTransform(prev => ({
      ...prev,
      scale: newScale,
    }));
  };

  const cropAndFinalize = async () => {
    if (!selectedImage || !template?.viewLayer || !canvasRef.current || !imageRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const image = imageRef.current;
    
    // 获取模板尺寸
    const templateWidth = template.viewLayer.width;
    const templateHeight = template.viewLayer.height;
    const templateAspectRatio = templateWidth / templateHeight;
    
    // 编辑器尺寸
    const editorSize = getEditorSize();
    const editorWidth = editorSize.width;
    const editorHeight = editorSize.height;
    
    // 使用预计算的图片显示信息
    if (!imageDisplayInfo) {
      console.error('图片显示信息未初始化');
      return;
    }
    
    const { width: displayWidth, height: displayHeight, initialX, initialY } = imageDisplayInfo;
    
    // 用户变换后的图片实际位置和尺寸
    const finalScale = imageTransform.scale;
    const finalWidth = displayWidth * finalScale;
    const finalHeight = displayHeight * finalScale;
    const finalX = initialX + imageTransform.x;
    const finalY = initialY + imageTransform.y;
    
    // 裁切框在编辑器中的位置
    const cropBoxX = (editorWidth - cropBoxSize.width) / 2;
    const cropBoxY = (editorHeight - cropBoxSize.height) / 2;
    
    // 裁切框相对于变换后图片的位置（归一化坐标 0-1）
    const relativeX = (cropBoxX - finalX) / finalWidth;
    const relativeY = (cropBoxY - finalY) / finalHeight;
    const relativeWidth = cropBoxSize.width / finalWidth;
    const relativeHeight = cropBoxSize.height / finalHeight;
    
    // 转换为原始图片像素坐标
    const cropX = Math.max(0, Math.min(image.naturalWidth, relativeX * image.naturalWidth));
    const cropY = Math.max(0, Math.min(image.naturalHeight, relativeY * image.naturalHeight));
    const cropWidth = Math.max(0, Math.min(image.naturalWidth - cropX, relativeWidth * image.naturalWidth));
    const cropHeight = Math.max(0, Math.min(image.naturalHeight - cropY, relativeHeight * image.naturalHeight));
    
    console.log('裁切计算:', {
      displaySize: { width: displayWidth, height: displayHeight },
      finalPosition: { x: finalX, y: finalY, width: finalWidth, height: finalHeight },
      cropBox: { x: cropBoxX, y: cropBoxY, width: cropBoxSize.width, height: cropBoxSize.height },
      relative: { x: relativeX, y: relativeY, width: relativeWidth, height: relativeHeight },
      final: { x: cropX, y: cropY, width: cropWidth, height: cropHeight }
    });
    
    // 设置输出画布尺寸
    let outputWidth, outputHeight;
    if (templateAspectRatio > 1) {
      outputWidth = Math.max(cropWidth, 800);
      outputHeight = Math.round(outputWidth / templateAspectRatio);
    } else {
      outputHeight = Math.max(cropHeight, 800);
      outputWidth = Math.round(outputHeight * templateAspectRatio);
    }
    
    canvas.width = outputWidth;
    canvas.height = outputHeight;
    ctx.clearRect(0, 0, outputWidth, outputHeight);

    // 绘制裁剪后的图片
    ctx.drawImage(
      image,
      cropX,
      cropY,
      cropWidth,
      cropHeight,
      0,
      0,
      outputWidth,
      outputHeight
    );

    // 转换为文件
    canvas.toBlob((blob) => {
      if (blob) {
        const editedFile = new File([blob], `edited_${selectedImage.name}`, {
          type: 'image/png'
        });
        
        setSelectedImage(editedFile);
        const url = URL.createObjectURL(blob);
        setEditedPreview(url);
        setEditedSize({ width: outputWidth, height: outputHeight });
        setStep('generate');
      }
    }, 'image/png');
  };

  const handleGenerate = async () => {
    if (!selectedImage || !template) return;
    
    setIsProcessing(true);
    setUploadProgress(0);
    
    try {
      const result = await apiService.generateFinalPsd(
        template.id, 
        selectedImage,
        (progress) => setUploadProgress(progress),
        forceResize,
        selectedComponent?.id,
        selectedStrokeWidth ?? null
      );
      
      if (result.success && result.data) {
        setGenerateResult(result.data);
        setStep('result');
        
        // 调用原始的onGenerate回调（如果提供）
        if (onGenerate) {
          await onGenerate(selectedImage, template);
        }
      } else {
        throw new Error(result.error || '生成失败');
      }
    } catch (error) {
      console.error('生成失败:', error);
      alert(error instanceof Error ? error.message : '生成失败，请重试');
    } finally {
      setIsProcessing(false);
      setUploadProgress(0);
    }
  };

  const handleDownload = async () => {
    if (!generateResult || !selectedImage || !template) return;
    
    try {
      // 生成组合文件名：用户图片名（不含扩展名）+ 模板名 + .psd
      const userImageName = selectedImage.name.replace(/\.[^/.]+$/, ''); // 去掉原始扩展名
      const templateName = template.name;
      const strokeSuffix = selectedStrokeWidth ? `_stroke_${selectedStrokeWidth}px` : '';
      const finalFileName = `${userImageName}_${templateName}${strokeSuffix}.psd`;
      
      await apiService.downloadFile(generateResult.resultId, finalFileName);
    } catch (error) {
      console.error('下载失败:', error);
      alert(error instanceof Error ? error.message : '下载失败，请重试');
    }
  };

  if (!isOpen || !template) return null;

  return (
    <div className="fixed inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">使用模板</h2>
            <p className="text-sm text-gray-500 mt-1">{template.name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* 步骤指示器 */}
          <div className="flex items-center justify-center mb-8">
              <div className="flex items-center space-x-4">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'component' ? 'bg-primary-600 text-white' : step === 'upload' || step === 'edit' || step === 'generate' || step === 'result' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>1</div>
              <div className="w-8 h-px bg-gray-300"></div>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'upload' ? 'bg-primary-600 text-white' : step === 'edit' || step === 'generate' || step === 'result' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>2</div>
              <div className="w-8 h-px bg-gray-300"></div>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'edit' ? 'bg-primary-600 text-white' : step === 'generate' || step === 'result' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>3</div>
              <div className="w-8 h-px bg-gray-300"></div>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'generate' ? 'bg-primary-600 text-white' : step === 'result' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>4</div>
              <div className="w-8 h-px bg-gray-300"></div>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'result' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>5</div>
            </div>
          </div>

          {/* 上传步骤 */}
          {step === 'upload' && (
            <div className="text-center">
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 hover:border-primary-400 transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">上传图片</h3>
                <p className="text-gray-500 mb-4">
                  点击或拖拽图片到此处上传
                </p>
                <p className="text-sm text-gray-400">
                  建议尺寸: {template.viewLayer?.width} × {template.viewLayer?.height}px
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </div>
          )}

          {/* 编辑步骤 - 新的固定选框编辑器 */}
          {step === 'edit' && imagePreview && (
            <div>
              {/* 操作按钮（上方） */}
              <div className="flex justify-end gap-2 mb-4">
                <button
                  onClick={() => setStep('upload')}
                  className="btn-secondary"
                >
                  重新选择
                </button>
                <button
                  onClick={cropAndFinalize}
                  className="btn-primary flex items-center space-x-2"
                >
                  <Crop className="w-4 h-4" />
                  <span>确认编辑</span>
                </button>
              </div>
              {/* 模板目标尺寸信息 */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="font-medium text-gray-900">模板目标尺寸</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {template.viewLayer?.width} × {template.viewLayer?.height} px
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">选框内像素尺寸</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {(() => {
                        if (!originalImageSize || !imageDisplayInfo) return '计算中...';
                        
                        // 计算选框在原始图像中对应的像素尺寸
                        const scaleX = originalImageSize.width / (imageDisplayInfo.width * imageTransform.scale);
                        const scaleY = originalImageSize.height / (imageDisplayInfo.height * imageTransform.scale);
                        
                        const actualWidth = Math.round(cropBoxSize.width * scaleX);
                        const actualHeight = Math.round(cropBoxSize.height * scaleY);
                        
                        return `${actualWidth} × ${actualHeight} px`;
                      })()}
                    </p>
                  </div>
                </div>
              </div>

              {/* 编辑选项 */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <label className="inline-flex items-center space-x-2 cursor-pointer select-none">
                      <span className="relative inline-flex items-center">
                        <input
                          type="checkbox"
                          id="forceResize"
                          checked={forceResize}
                          onChange={(e) => setForceResize(e.target.checked)}
                          className="peer sr-only"
                        />
                        <span
                          aria-hidden
                          className="h-4 w-4 rounded-md border border-gray-300 bg-white shadow-sm flex items-center justify-center transition
                                     hover:border-primary-400 peer-focus:ring-2 peer-focus:ring-primary-500 peer-focus:ring-offset-2
                                     peer-checked:bg-primary-600 peer-checked:border-primary-600 peer-checked:text-white"
                        >
                          <Check className="h-3 w-3 opacity-0 transition-opacity peer-checked:opacity-100" />
                        </span>
                      </span>
                      <span className="flex items-center space-x-2 text-sm font-medium text-gray-700">
                        <AlignCenter className="w-4 h-4" />
                        <span>强制对齐到模板尺寸</span>
                      </span>
                    </label>
                  </div>
                    
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setShowReferenceOverlay(!showReferenceOverlay)}
                      className={`flex items-center space-x-2 px-3 py-2 border rounded-lg transition-colors ${
                        showReferenceOverlay 
                          ? 'bg-primary-50 border-primary-300 text-primary-700' 
                          : 'bg-white border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {showReferenceOverlay ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                      <span className="text-sm">对比模式</span>
                    </button>
                    <button
                      onClick={resetEdit}
                      className="flex items-center space-x-2 px-3 py-2 bg-white border rounded-lg hover:bg-gray-50"
                    >
                      <RotateCcw className="w-4 h-4" />
                      <span className="text-sm">重置</span>
                    </button>
                  </div>
                </div>
                
                {forceResize && (
                  <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">
                      <strong>强制对齐说明：</strong>选中后，生成时会将选框内容强制调整到模板要求尺寸（{template.viewLayer?.width} × {template.viewLayer?.height}px），然后进行裁切处理。
                    </p>
                  </div>
                )}
                
                {showReferenceOverlay && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-700">
                      <strong>对比模式已开启：</strong>选框中央显示半透明参考图，拖动和缩放图片以对齐参考内容。
                    </p>
                  </div>
                )}
              </div>

              {/* 新的图片编辑器 */}
              <div className="w-full">
                <div ref={editorRef} className="relative bg-gray-100 rounded-lg overflow-hidden" style={{ width: '100%', height: '500px' }} onWheel={handleWheel}>
                  {/* 图片容器 */}
                  {imageDisplayInfo && (
                    <div
                      className="absolute select-none group"
                      style={{
                        left: `${imageDisplayInfo.initialX}px`,
                        top: `${imageDisplayInfo.initialY}px`,
                        transform: `translate(${imageTransform.x}px, ${imageTransform.y}px) scale(${imageTransform.scale}) rotate(${imageTransform.rotation}deg)`,
                        transformOrigin: 'left top',
                        width: `${imageDisplayInfo.width}px`,
                        height: `${imageDisplayInfo.height}px`,
                      }}
                    >
                      {/* 图片主体（可拖拽移动） */}
                      <img
                        ref={imageRef}
                        src={imagePreview}
                        alt="编辑预览"
                        className="max-w-none cursor-move"
                        style={{
                          width: 'auto',
                          height: `${imageDisplayInfo.height}px`,
                        }}
                        draggable={false}
                        onMouseDown={handleImageMove}
                      />
                      
                      {/* 四个角的缩放控制点 */}
                      <div
                        className="absolute -top-2 -left-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-nw-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'tl')}
                        title="左上角缩放"
                      />
                      <div
                        className="absolute -top-2 -right-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-ne-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'tr')}
                        title="右上角缩放"
                      />
                      <div
                        className="absolute -bottom-2 -left-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-sw-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'bl')}
                        title="左下角缩放"
                      />
                      <div
                        className="absolute -bottom-2 -right-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-se-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'br')}
                        title="右下角缩放"
                      />
                    </div>
                  )}
                  
                  {/* 固定的裁切框（不可拖拽） */}
                  <div
                    className="absolute border-2 border-blue-500 bg-blue-500 bg-opacity-10 pointer-events-none"
                    style={{
                      left: `${(getEditorSize().width - cropBoxSize.width) / 2}px`,
                      top: `${(getEditorSize().height - cropBoxSize.height) / 2}px`,
                      width: `${cropBoxSize.width}px`,
                      height: `${cropBoxSize.height}px`,
                    }}
                  >
                    {/* 裁切框角标 */}
                    <div className="absolute -top-1 -left-1 w-3 h-3 border-2 border-blue-500 bg-white rounded-full"></div>
                    <div className="absolute -top-1 -right-1 w-3 h-3 border-2 border-blue-500 bg-white rounded-full"></div>
                    <div className="absolute -bottom-1 -left-1 w-3 h-3 border-2 border-blue-500 bg-white rounded-full"></div>
                    <div className="absolute -bottom-1 -right-1 w-3 h-3 border-2 border-blue-500 bg-white rounded-full"></div>
                  </div>
                  
                  {/* 参考图叠加层 */}
                  {showReferenceOverlay && template && (
                    <div
                      className="absolute pointer-events-none"
                      style={{
                        left: `${(getEditorSize().width - cropBoxSize.width) / 2}px`,
                        top: `${(getEditorSize().height - cropBoxSize.height) / 2}px`,
                        width: `${cropBoxSize.width}px`,
                        height: `${cropBoxSize.height}px`,
                        overflow: 'hidden',
                      }}
                    >
                      <img
                        src={`${API_BASE_URL}/api/templates/${template.id}/reference`}
                        alt="Reference对比"
                        className="w-full h-full object-cover opacity-100"
                      />
                      
                      <div className="absolute top-1 left-1 bg-blue-600 bg-opacity-80 text-white text-xs px-1 py-0.5 rounded">
                        参考图
                      </div>
                    </div>
                  )}
                  
                  {/* 编辑提示 */}
                  <div className="absolute top-2 left-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded z-20">
                    拖拽图片移动位置，悬停显示角部控制点进行缩放
                  </div>
                </div>
              </div>

              {/* 底部按钮移除，统一移动到上方 */}
            </div>
          )}

          {/* 部件选择步骤 */}
          {step === 'component' && (
            <div className="text-center">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
                <Package className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">选择部件（可选）</h3>
                <p className="text-gray-600">
                  选择一个部件添加到最终结果中，或直接上传图片继续
                </p>
              </div>

              {componentsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-gray-500">加载部件中...</div>
                </div>
              ) : availableComponents.length === 0 ? (
                <div className="text-center py-8">
                  <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 mb-4">此模板暂无可选部件</p>
                  <button
                    onClick={() => setStep('upload')}
                    className="btn-primary"
                  >
                    前往上传图片
                  </button>
                </div>
              ) : (
                <>
                  {/* 操作按钮（上方） */}
                  <div className="flex justify-center mb-4">
                    <button
                      onClick={() => setStep('upload')}
                      className="btn-primary flex items-center space-x-2"
                    >
                      <span>上传图片</span>
                      <span className="text-xs bg-white/20 px-2 py-0.5 rounded">
                        {selectedComponent ? selectedComponent.name : '无部件'}
                      </span>
                    </button>
                  </div>

                  {/* 部件选择器 */}
                  <div className="mb-6 flex justify-center">
                    <div
                      ref={componentSectionRef}
                      className="grid grid-cols-1 gap-4"
                      style={{ width: componentSelectWidth ? `${componentSelectWidth}px` : undefined }}
                    >
                      {/* 部件选项 */}
                      {availableComponents.map((component) => (
                        <div 
                          key={component.id}
                          className={`border-2 rounded-lg p-2 cursor-pointer transition-colors ${
                            selectedComponent?.id === component.id 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                          onClick={() => setSelectedComponent(prev => prev?.id === component.id ? null : component)}
                        >
                          <div 
                            className="relative rounded-lg overflow-hidden"
                            style={{
                              aspectRatio: `${template.viewLayer?.width || 1} / ${template.viewLayer?.height || 1}`,
                              width: '100%',
                              backgroundColor: 'rgb(128, 128, 128)'
                            }}
                          >
                            <div className="absolute inset-2">
                              <img
                                src={`${API_BASE_URL}/api/templates/${template.id}/components/${component.id}`}
                                alt={component.name}
                                className="w-full h-full object-contain"
                                onError={(e) => {
                                  const img = e.target as HTMLImageElement;
                                  img.style.display = 'none';
                                  const parent = img.parentElement;
                                  if (parent) {
                                    (parent as HTMLElement).innerHTML = '<div class="w-full h-full flex items-center justify-center text-gray-200"><svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z\"></path></svg></div>';
                                  }
                                }}
                              />
                            </div>
                          </div>
                          <div className="text-center mt-2">
                            <p className="text-sm font-medium text-gray-900 truncate">{component.name}</p>
                            <p className="text-xs text-gray-500">PNG · {Math.round(component.size / 1024)}KB</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 底部按钮移除，统一移动到上方 */}
                </>
              )}
            </div>
          )}

          {/* 生成步骤 */}
          {step === 'generate' && (
            <div className="text-center">
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
                <Check className="w-12 h-12 text-green-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">图片准备就绪</h3>
                <p className="text-gray-600">
                  图片已处理完成，可以开始生成最终结果
                </p>
              </div>

              {/* 操作按钮（上方） */}
              <div className="flex justify-end gap-2 mb-4">
                <button
                  onClick={() => setStep('upload')}
                  className="btn-secondary"
                  disabled={isProcessing}
                >
                  重新选择
                </button>
                <button
                  onClick={handleGenerate}
                  className="btn-primary"
                  disabled={isProcessing}
                >
                  {isProcessing ? '生成中...' : '开始生成'}
                </button>
              </div>

              {/* 生成进度（按钮下方，预览上方） */}
              {isProcessing && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center justify-center mb-2">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    <span className="ml-2 text-blue-700">生成中...</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-blue-600 mt-2">{uploadProgress}%</p>
                </div>
              )}

              {/* 裁切结果预览与尺寸 */}
              <div className="card p-4 mb-6 text-left">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-gray-900">裁切模板选择</h4>
                  <div className="flex items-center gap-2">
                    {/* Stroke版本选择（存在配置时显示） */}
                    {template?.strokeConfig && template.strokeConfig.length > 0 && (
                      <select
                        className="text-xs border-gray-300 rounded px-2 py-1 bg-white"
                        value={selectedStrokeWidth ?? ''}
                        onChange={(e) => {
                          const v = e.target.value;
                          setSelectedStrokeWidth(v ? Number(v) : null);
                          setShowPreviewOverlay(true);
                        }}
                      >
                        <option value="">原始</option>
                        {[...template.strokeConfig].sort((a, b) => a - b).map(w => (
                          <option key={w} value={w}>{w}px描边</option>
                        ))}
                      </select>
                    )}

                    {/* 透明度（仅叠加时可用） */}
                    {showPreviewOverlay && (
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-500">透明度</span>
                        <input
                          type="range"
                          min={10}
                          max={100}
                          step={5}
                          value={overlayOpacity}
                          onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                        />
                      </div>
                    )}

                    <button
                      onClick={() => setShowPreviewOverlay(!showPreviewOverlay)}
                      className={`flex items-center space-x-1 px-2 py-1 text-xs border rounded transition-colors ${
                        showPreviewOverlay 
                          ? 'bg-primary-50 border-primary-300 text-primary-700' 
                          : 'bg-white border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {showPreviewOverlay ? (
                        <EyeOff className="w-3 h-3" />
                      ) : (
                        <Eye className="w-3 h-3" />
                      )}
                      <span>选择模板</span>
                    </button>
                  </div>
                </div>
                <div className="w-full relative">
                  <img
                    src={editedPreview || imagePreview || ''}
                    alt="裁切预览"
                    className="w-full h-auto rounded border border-gray-200"
                    onLoad={(e) => {
                      const img = e.currentTarget as HTMLImageElement;
                      setCutPreviewSize({ width: img.naturalWidth, height: img.naturalHeight });
                    }}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  
                  {/* Reference图层叠加 */}
                  {showPreviewOverlay && template && (
                    <div className="absolute inset-0 rounded border border-gray-200 overflow-hidden">
                      <img
                        src={selectedStrokeWidth
                          ? `${API_BASE_URL}/api/templates/${template.id}/stroke/${selectedStrokeWidth}/reference`
                          : `${API_BASE_URL}/api/templates/${template.id}/reference`}
                        alt="Reference对比"
                        className="w-full h-full object-cover"
                        style={{ opacity: Math.max(0, Math.min(1, overlayOpacity / 100)) }}
                      />
                      
                      <div className="absolute top-2 left-2 bg-blue-600 bg-opacity-80 text-white text-xs px-2 py-1 rounded">
                        {selectedStrokeWidth ? `Stroke ${selectedStrokeWidth}px` : '原始'}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 部件预览 */}
              {selectedComponent && (
                <div className="card p-4 mb-6 text-left">
                  <h4 className="font-medium text-gray-900 mb-3">
                    {(() => {
                      // 合并显示：部件预览（名称｜最终尺寸）
                      const tplW = template.viewLayer?.width;
                      const tplH = template.viewLayer?.height;
                      const nonForceTarget = editedSize || cutPreviewSize || originalImageSize;
                      const decided = (forceResize && tplW && tplH)
                        ? { width: tplW, height: tplH }
                        : (nonForceTarget ? { width: Math.round(nonForceTarget.width), height: Math.round(nonForceTarget.height) } : null);
                      const sizeText = decided ? `｜${decided.width} × ${decided.height} px` : '';
                      return `部件预览（${selectedComponent.name}${sizeText}）`;
                    })()}
                  </h4>
                  <div 
                    className="w-full bg-gray-500 rounded border border-gray-200 p-3"
                    style={{
                      aspectRatio: `${template.viewLayer?.width || 1} / ${template.viewLayer?.height || 1}`
                    }}
                  >
                    <img
                      src={`${API_BASE_URL}/api/templates/${template.id}/components/${selectedComponent.id}`}
                      alt={selectedComponent.name}
                      className="w-full h-full object-contain rounded"
                      onLoad={(e) => {
                        const img = e.currentTarget as HTMLImageElement;
                        setComponentPreviewSize({ width: img.naturalWidth, height: img.naturalHeight });
                      }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                </div>
              )}

              {/* 底部按钮移除，统一移动到上方 */}
            </div>
          )}

          {/* 结果步骤 */}
          {step === 'result' && generateResult && (
            <div className="text-center">

              {/* 操作按钮（上方） */}
              <div className="flex justify-center space-x-4 mb-4">
                <button
                  onClick={() => setStep('upload')}
                  className="btn-secondary"
                >
                  生成新的
                </button>
                <button
                  onClick={handleDownload}
                  className="btn-primary flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>下载PSD</span>
                </button>
                <button
                  onClick={onClose}
                  className="btn-primary"
                >
                  完成
                </button>
              </div>

              {/* 生成完成 + 最终裁切尺寸（合并卡片，按钮下方） */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6 text-left">
                <div className="flex items-start">
                  <Check className="w-6 h-6 text-green-600 mr-3 mt-0.5" />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-1">生成完成！</h3>
                    <p className="text-sm text-gray-700 mb-2">您的PSD文件已成功生成，可以预览和下载。</p>
                    <p className="text-sm text-gray-600">
                      最终裁切尺寸：
                      {finalPreviewSize
                        ? `${finalPreviewSize.width} × ${finalPreviewSize.height} px`
                        : '加载中...'}
                    </p>
                  </div>
                </div>
              </div>

              {/* 最终预览，背景使用50%灰以便查看透明区域 */}
              {generateResult.previewPath && (
                <div className="card p-4 mb-6 text-left">
                  <h4 className="font-medium text-gray-900 mb-3">
                    {(() => {
                      // 显示最终生成图片的实际尺寸
                      const s = finalPreviewSize;
                      const sizeText = s ? `（${Math.round(s.width)} × ${Math.round(s.height)} px）` : '';
                      return `最终预览${sizeText}`;
                    })()}
                  </h4>
                  <div className="w-full rounded p-2 md:p-3" style={{ backgroundColor: 'rgb(128,128,128)' }}>
                    <img
                      src={apiService.getPreviewUrl(generateResult.resultId)}
                      alt="生成结果预览"
                      className="w-full h-auto"
                      onLoad={(e) => {
                        const img = e.currentTarget as HTMLImageElement;
                        setFinalPreviewSize({ width: img.naturalWidth, height: img.naturalHeight });
                      }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                </div>
              )}
              {/* 底部按钮移除，统一移动到上方 */}
            </div>
          )}
        </div>

        {/* 隐藏的canvas用于图片处理 */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  );
};
