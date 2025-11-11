import React, { useState, useRef, useEffect } from 'react';
import { X, Upload, Crop, RotateCcw } from 'lucide-react';
import { apiService } from '../services/api.ts';

interface DieElementEditorProps {
  isOpen: boolean;
  onClose: () => void;
  elementId: string;
  elementName: string;
  cutSize: { width: number; height: number };
  referenceSize: { width: number; height: number };
  onSuccess?: () => void;
}

interface ImageTransform {
  x: number;
  y: number;
  scale: number;
  rotation: number;
}

export const DieElementEditor: React.FC<DieElementEditorProps> = ({
  isOpen,
  onClose,
  elementId,
  elementName,
  cutSize,
  referenceSize,
  onSuccess,
}) => {
  const [step, setStep] = useState<'upload' | 'edit' | 'processing'>('upload');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageTransform, setImageTransform] = useState<ImageTransform>({
    x: 0,
    y: 0,
    scale: 1,
    rotation: 0,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [imageDisplayInfo, setImageDisplayInfo] = useState<{
    width: number;
    height: number;
    initialX: number;
    initialY: number
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  // 将像素转换为厘米（假设300 DPI）
  const cmToPixel = (cm: number): number => {
    return Math.round(cm * (300 / 2.54));
  };

  // 获取编辑器尺寸
  const getEditorSize = () => {
    if (!editorRef.current) return { width: 800, height: 500 };
    const rect = editorRef.current.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  };

  useEffect(() => {
    if (!isOpen) {
      // 重置状态
      setStep('upload');
      setSelectedImage(null);
      setImagePreview(null);
      setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
      setIsProcessing(false);
      setImageDisplayInfo(null);
      setErrorMessage('');
    }
  }, [isOpen]);

  // 图片上传处理
  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setErrorMessage('请选择图片文件');
      return;
    }

    setSelectedImage(file);
    setErrorMessage('');

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setImagePreview(result);

      const img = new Image();
      img.onload = () => {
        // 计算裁切框尺寸（基于cutSize，转换为像素）
        const cutPixelWidth = cmToPixel(cutSize.width);
        const cutPixelHeight = cmToPixel(cutSize.height);

        // 检查图片尺寸是否与裁切尺寸一致（允许±5像素的误差）
        const widthMatch = Math.abs(img.naturalWidth - cutPixelWidth) <= 5;
        const heightMatch = Math.abs(img.naturalHeight - cutPixelHeight) <= 5;

        if (widthMatch && heightMatch) {
          // 尺寸匹配，直接上传
          autoSaveImage(file);
          return;
        }

        setTimeout(() => {
          const aspectRatio = cutPixelWidth / cutPixelHeight;

          const editorSize = getEditorSize();

          // 计算裁切框在编辑器中的显示尺寸（占80%）
          const maxCropWidth = editorSize.width * 0.8;
          const maxCropHeight = editorSize.height * 0.8;

          let displayCropWidth, displayCropHeight;
          if (aspectRatio > 1) {
            displayCropWidth = maxCropWidth;
            displayCropHeight = maxCropWidth / aspectRatio;
            if (displayCropHeight > maxCropHeight) {
              displayCropHeight = maxCropHeight;
              displayCropWidth = maxCropHeight * aspectRatio;
            }
          } else {
            displayCropWidth = maxCropWidth;
            displayCropHeight = maxCropWidth / aspectRatio;
            if (displayCropHeight > maxCropHeight) {
              displayCropHeight = maxCropHeight;
              displayCropWidth = maxCropHeight * aspectRatio;
            }
          }

          // 计算图片初始显示尺寸
          const displayHeight = editorSize.height * 0.8;
          const displayWidth = (img.width / img.height) * displayHeight;
          const initialX = (editorSize.width - displayWidth) / 2;
          const initialY = (editorSize.height - displayHeight) / 2;

          setImageDisplayInfo({
            width: displayWidth,
            height: displayHeight,
            initialX,
            initialY,
          });

          setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
          setStep('edit');
        }, 100);
      };
      img.src = result;
    };
    reader.readAsDataURL(file);
  };

  // 自动保存图片（尺寸匹配时）
  const autoSaveImage = async (file: File) => {
    setIsProcessing(true);
    setStep('processing');
    setErrorMessage('');

    try {
      const response = await apiService.generateDieMaterial(elementId, file);

      if (response.success) {
        // 延迟关闭，给用户看到成功提示
        setTimeout(() => {
          if (onSuccess) {
            onSuccess();
          }
          onClose();
        }, 1000);
      } else {
        throw new Error(response.error || '生成素材失败');
      }
    } catch (error) {
      console.error('生成素材失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '生成素材失败');
      setStep('upload');
    } finally {
      setIsProcessing(false);
    }
  };

  // 重置编辑
  const resetEdit = () => {
    setImageTransform({ x: 0, y: 0, scale: 1, rotation: 0 });
  };

  // 图片拖拽移动
  const handleImageMove = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX - imageTransform.x;
    const startY = e.clientY - imageTransform.y;

    const handleMouseMove = (e: MouseEvent) => {
      setImageTransform((prev) => ({
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

  // 图片缩放
  const handleImageScale = (e: React.MouseEvent, corner: 'tl' | 'tr' | 'bl' | 'br') => {
    e.preventDefault();
    e.stopPropagation();

    if (!imageDisplayInfo) return;

    const startMouseX = e.clientX;
    const startMouseY = e.clientY;
    const startScale = imageTransform.scale;
    const startX = imageTransform.x;
    const startY = imageTransform.y;

    const imageCenterX = imageDisplayInfo.initialX + startX + (imageDisplayInfo.width * startScale) / 2;
    const imageCenterY = imageDisplayInfo.initialY + startY + (imageDisplayInfo.height * startScale) / 2;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startMouseX;
      const deltaY = e.clientY - startMouseY;

      let scaleMultiplier = 1;
      switch (corner) {
        case 'tl':
          scaleMultiplier = 1 + (-deltaX - deltaY) / 200;
          break;
        case 'tr':
          scaleMultiplier = 1 + (deltaX - deltaY) / 200;
          break;
        case 'bl':
          scaleMultiplier = 1 + (-deltaX + deltaY) / 200;
          break;
        case 'br':
          scaleMultiplier = 1 + (deltaX + deltaY) / 200;
          break;
      }

      const newScale = Math.max(0.1, Math.min(5, startScale * scaleMultiplier));

      const newWidth = imageDisplayInfo.width * newScale;
      const newHeight = imageDisplayInfo.height * newScale;
      const newX = imageCenterX - imageDisplayInfo.initialX - newWidth / 2;
      const newY = imageCenterY - imageDisplayInfo.initialY - newHeight / 2;

      setImageTransform((prev) => ({
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

  // 滚轮缩放
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(3, imageTransform.scale * scaleFactor));

    setImageTransform((prev) => ({
      ...prev,
      scale: newScale,
    }));
  };

  // 裁切并保存
  const cropAndSave = async () => {
    if (!selectedImage || !canvasRef.current || !imageRef.current || !imageDisplayInfo) return;

    setIsProcessing(true);
    setErrorMessage('');

    try {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error('无法获取Canvas上下文');
      }

      const image = imageRef.current;
      const editorSize = getEditorSize();

      // 裁切框像素尺寸
      const cutPixelWidth = cmToPixel(cutSize.width);
      const cutPixelHeight = cmToPixel(cutSize.height);

      // 裁切框在编辑器中的显示尺寸
      const aspectRatio = cutPixelWidth / cutPixelHeight;
      const maxCropWidth = editorSize.width * 0.8;
      const maxCropHeight = editorSize.height * 0.8;

      let displayCropWidth, displayCropHeight;
      if (aspectRatio > 1) {
        displayCropWidth = maxCropWidth;
        displayCropHeight = maxCropWidth / aspectRatio;
        if (displayCropHeight > maxCropHeight) {
          displayCropHeight = maxCropHeight;
          displayCropWidth = maxCropHeight * aspectRatio;
        }
      } else {
        displayCropWidth = maxCropWidth;
        displayCropHeight = maxCropWidth / aspectRatio;
        if (displayCropHeight > maxCropHeight) {
          displayCropHeight = maxCropHeight;
          displayCropWidth = maxCropHeight * aspectRatio;
        }
      }

      const cropBoxX = (editorSize.width - displayCropWidth) / 2;
      const cropBoxY = (editorSize.height - displayCropHeight) / 2;

      // 用户变换后的图片位置
      const finalScale = imageTransform.scale;
      const finalWidth = imageDisplayInfo.width * finalScale;
      const finalHeight = imageDisplayInfo.height * finalScale;
      const finalX = imageDisplayInfo.initialX + imageTransform.x;
      const finalY = imageDisplayInfo.initialY + imageTransform.y;

      // 裁切框相对于图片的位置（归一化）
      const relativeX = (cropBoxX - finalX) / finalWidth;
      const relativeY = (cropBoxY - finalY) / finalHeight;
      const relativeWidth = displayCropWidth / finalWidth;
      const relativeHeight = displayCropHeight / finalHeight;

      // 转换为原始图片像素坐标
      const cropX = Math.max(0, Math.min(image.naturalWidth, relativeX * image.naturalWidth));
      const cropY = Math.max(0, Math.min(image.naturalHeight, relativeY * image.naturalHeight));
      const cropWidth = Math.max(0, Math.min(image.naturalWidth - cropX, relativeWidth * image.naturalWidth));
      const cropHeight = Math.max(0, Math.min(image.naturalHeight - cropY, relativeHeight * image.naturalHeight));

      // 生成裁切结果
      canvas.width = cutPixelWidth;
      canvas.height = cutPixelHeight;
      ctx.clearRect(0, 0, cutPixelWidth, cutPixelHeight);
      ctx.drawImage(
        image,
        cropX,
        cropY,
        cropWidth,
        cropHeight,
        0,
        0,
        cutPixelWidth,
        cutPixelHeight
      );

      // 转换为Blob并上传
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/png');
      });

      if (!blob) {
        throw new Error('生成图片失败');
      }

      const file = new File([blob], `${elementName}_material.png`, { type: 'image/png' });

      // 调用API上传
      const response = await apiService.generateDieMaterial(elementId, file);

      if (response.success) {
        setStep('processing');
        // 延迟关闭，给用户看到成功提示
        setTimeout(() => {
          if (onSuccess) {
            onSuccess();
          }
          onClose();
        }, 1000);
      } else {
        throw new Error(response.error || '生成素材失败');
      }
    } catch (error) {
      console.error('生成素材失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '生成素材失败');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">生成刀模素材</h2>
            <p className="text-sm text-gray-500 mt-1">
              {elementName} - 裁切尺寸: {cutSize.width} × {cutSize.height} cm
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            disabled={isProcessing}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* 上传步骤 */}
          {step === 'upload' && (
            <div className="text-center">
              <div
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 hover:border-primary-400 transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">上传图片</h3>
                <p className="text-gray-500 mb-4">点击或拖拽图片到此处上传</p>
                <p className="text-sm text-gray-400">
                  将裁切为 {cutSize.width} × {cutSize.height} cm (约 {cmToPixel(cutSize.width)} × {cmToPixel(cutSize.height)} 像素)
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              {errorMessage && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {errorMessage}
                </div>
              )}
            </div>
          )}

          {/* 编辑步骤 */}
          {step === 'edit' && imagePreview && (
            <div>
              {/* 操作按钮 */}
              <div className="flex justify-end gap-2 mb-4">
                <button onClick={() => setStep('upload')} className="btn-secondary">
                  重新选择
                </button>
                <button onClick={resetEdit} className="btn-secondary flex items-center space-x-2">
                  <RotateCcw className="w-4 h-4" />
                  <span>重置</span>
                </button>
                <button
                  onClick={cropAndSave}
                  className="btn-primary flex items-center space-x-2"
                  disabled={isProcessing}
                >
                  <Crop className="w-4 h-4" />
                  <span>{isProcessing ? '处理中...' : '确认裁切'}</span>
                </button>
              </div>

              {/* 尺寸信息 */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="font-medium text-gray-900">裁切尺寸 (红框)</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {cutSize.width} × {cutSize.height} cm ({cmToPixel(cutSize.width)} × {cmToPixel(cutSize.height)} px)
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">参考尺寸 (蓝框)</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {referenceSize.width} × {referenceSize.height} cm ({cmToPixel(referenceSize.width)} × {cmToPixel(referenceSize.height)} px)
                    </p>
                  </div>
                </div>
              </div>

              {/* 图片编辑器 */}
              <div className="w-full">
                <div
                  ref={editorRef}
                  className="relative bg-gray-100 rounded-lg overflow-hidden"
                  style={{ width: '100%', height: '500px' }}
                  onWheel={handleWheel}
                >
                  {/* 图片 */}
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
                      />
                      <div
                        className="absolute -top-2 -right-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-ne-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'tr')}
                      />
                      <div
                        className="absolute -bottom-2 -left-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-sw-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'bl')}
                      />
                      <div
                        className="absolute -bottom-2 -right-2 w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-se-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        onMouseDown={(e) => handleImageScale(e, 'br')}
                      />
                    </div>
                  )}

                  {/* 裁切框（红色实线） */}
                  {(() => {
                    const editorSize = getEditorSize();
                    const cutPixelWidth = cmToPixel(cutSize.width);
                    const cutPixelHeight = cmToPixel(cutSize.height);
                    const aspectRatio = cutPixelWidth / cutPixelHeight;
                    const maxCropWidth = editorSize.width * 0.8;
                    const maxCropHeight = editorSize.height * 0.8;

                    let displayCropWidth, displayCropHeight;
                    if (aspectRatio > 1) {
                      displayCropWidth = maxCropWidth;
                      displayCropHeight = maxCropWidth / aspectRatio;
                      if (displayCropHeight > maxCropHeight) {
                        displayCropHeight = maxCropHeight;
                        displayCropWidth = maxCropHeight * aspectRatio;
                      }
                    } else {
                      displayCropWidth = maxCropWidth;
                      displayCropHeight = maxCropWidth / aspectRatio;
                      if (displayCropHeight > maxCropHeight) {
                        displayCropHeight = maxCropHeight;
                        displayCropWidth = maxCropHeight * aspectRatio;
                      }
                    }

                    const cropBoxX = (editorSize.width - displayCropWidth) / 2;
                    const cropBoxY = (editorSize.height - displayCropHeight) / 2;

                    return (
                      <div
                        className="absolute border-2 border-red-500 bg-red-500 bg-opacity-10 pointer-events-none"
                        style={{
                          left: `${cropBoxX}px`,
                          top: `${cropBoxY}px`,
                          width: `${displayCropWidth}px`,
                          height: `${displayCropHeight}px`,
                        }}
                      >
                        {/* 裁切框角标 */}
                        <div className="absolute -top-1 -left-1 w-3 h-3 border-2 border-red-500 bg-white rounded-full"></div>
                        <div className="absolute -top-1 -right-1 w-3 h-3 border-2 border-red-500 bg-white rounded-full"></div>
                        <div className="absolute -bottom-1 -left-1 w-3 h-3 border-2 border-red-500 bg-white rounded-full"></div>
                        <div className="absolute -bottom-1 -right-1 w-3 h-3 border-2 border-red-500 bg-white rounded-full"></div>
                      </div>
                    );
                  })()}

                  {/* 参考框（蓝色虚线，半透明） */}
                  {(() => {
                    const editorSize = getEditorSize();
                    const refPixelWidth = cmToPixel(referenceSize.width);
                    const refPixelHeight = cmToPixel(referenceSize.height);
                    const aspectRatio = refPixelWidth / refPixelHeight;
                    const maxRefWidth = editorSize.width * 0.8;
                    const maxRefHeight = editorSize.height * 0.8;

                    let displayRefWidth, displayRefHeight;
                    if (aspectRatio > 1) {
                      displayRefWidth = maxRefWidth;
                      displayRefHeight = maxRefWidth / aspectRatio;
                      if (displayRefHeight > maxRefHeight) {
                        displayRefHeight = maxRefHeight;
                        displayRefWidth = maxRefHeight * aspectRatio;
                      }
                    } else {
                      displayRefWidth = maxRefWidth;
                      displayRefHeight = maxRefWidth / aspectRatio;
                      if (displayRefHeight > maxRefHeight) {
                        displayRefHeight = maxRefHeight;
                        displayRefWidth = maxRefHeight * aspectRatio;
                      }
                    }

                    const refBoxX = (editorSize.width - displayRefWidth) / 2;
                    const refBoxY = (editorSize.height - displayRefHeight) / 2;

                    return (
                      <div
                        className="absolute border-2 border-dashed border-blue-500 pointer-events-none"
                        style={{
                          left: `${refBoxX}px`,
                          top: `${refBoxY}px`,
                          width: `${displayRefWidth}px`,
                          height: `${displayRefHeight}px`,
                          opacity: 0.3,
                        }}
                      />
                    );
                  })()}

                  {/* 提示文字 */}
                  <div className="absolute top-2 left-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded z-20">
                    拖拽图片移动位置，悬停显示角部控制点进行缩放
                  </div>
                  <div className="absolute bottom-2 left-2 space-y-1 z-20">
                    <div className="bg-red-500 bg-opacity-70 text-white text-xs px-2 py-1 rounded">
                      红框：裁切线 ({cutSize.width} × {cutSize.height} cm)
                    </div>
                    <div className="bg-blue-600 bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                      蓝框：参考线 ({referenceSize.width} × {referenceSize.height} cm)
                    </div>
                  </div>
                </div>
              </div>

              {/* 错误信息 */}
              {errorMessage && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {errorMessage}
                </div>
              )}
            </div>
          )}

          {/* 处理中步骤 */}
          {step === 'processing' && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">正在生成素材...</h3>
              <p className="text-gray-500">请稍候</p>
            </div>
          )}
        </div>

        {/* 隐藏的canvas用于图片处理 */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  );
};
