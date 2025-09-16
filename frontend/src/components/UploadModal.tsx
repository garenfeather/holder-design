import React, { useState, useCallback } from 'react';
import { X, Upload, FileText, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { validatePSDFile, formatFileSize } from '../utils/index.ts';
import { apiService } from '../services/api.ts';
import { UploadProgress } from '../types/index.ts';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: (templateId: string) => void;
  onUploadError?: (error: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  onUploadError
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  }, []);

  const handleFileSelection = useCallback((file: File) => {
    // 验证文件
    const validation = validatePSDFile(file);
    if (!validation.valid) {
      onUploadError?.(validation.error!);
      return;
    }

    setSelectedFile(file);
  }, [onUploadError]);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setUploadProgress({
      fileName: selectedFile.name,
      progress: 0,
      status: 'uploading'
    });

    try {
      const result = await apiService.uploadTemplate(
        selectedFile,
        (progress) => {
          setUploadProgress(prev => prev ? { ...prev, progress } : null);
        }
      );

      if (result.success && result.data) {
        setUploadProgress(prev => prev ? { ...prev, status: 'processing' } : null);
        
        setUploadProgress(prev => prev ? { ...prev, status: 'complete', progress: 100 } : null);
        
        // 延迟一下显示完成状态
        setTimeout(() => {
          setUploadProgress(null);
          setSelectedFile(null);
          onUploadSuccess?.(result.data!.id);
          onClose();
        }, 1500);
        
      } else {
        throw new Error(result.error || '上传失败');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '上传失败';
      setUploadProgress({
        fileName: selectedFile.name,
        progress: 0,
        status: 'error',
        error: errorMessage
      });
      onUploadError?.(errorMessage);
    }
  }, [selectedFile, onUploadSuccess, onUploadError, onClose]);

  const handleCancel = useCallback(() => {
    setSelectedFile(null);
    setUploadProgress(null);
    onClose();
  }, [onClose]);

  const handleModalClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      handleCancel();
    }
  };

  if (!isOpen) return null;

  const renderUploadZone = () => (
    <div
      className={`upload-zone ${isDragOver ? 'upload-zone-active' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="space-y-4">
        <div className="flex justify-center">
          <Upload 
            className={`w-12 h-12 ${isDragOver ? 'text-primary-600' : 'text-gray-400'} transition-colors`}
          />
        </div>
        
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-gray-900">
            {isDragOver ? '释放文件以上传' : '上传 PSD 模板'}
          </h3>
          <p className="text-sm text-gray-500">
            拖拽 PSD 文件到此处，或
            <label className="text-primary-600 hover:text-primary-700 cursor-pointer ml-1">
              点击选择文件
              <input
                type="file"
                accept=".psd"
                onChange={handleFileInputChange}
                className="hidden"
              />
            </label>
          </p>
          <p className="text-xs text-gray-400">
            支持最大 100MB 的 .psd 文件
          </p>
        </div>
      </div>
    </div>
  );

  const renderFilePreview = () => (
    <div className="space-y-4">
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <FileText className="w-12 h-12 text-primary-600" />
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-medium text-gray-900 truncate">
            {selectedFile?.name}
          </h3>
          <p className="text-sm text-gray-500">
            {selectedFile && formatFileSize(selectedFile.size)}
          </p>
        </div>
      </div>
      
      <div className="flex space-x-3">
        <button
          onClick={handleUpload}
          className="btn-primary flex-1"
          disabled={!!uploadProgress}
        >
          <Upload className="w-4 h-4 mr-2" />
          开始上传
        </button>
        <button
          onClick={handleCancel}
          className="btn-secondary"
        >
          取消
        </button>
      </div>
    </div>
  );

  const renderUploadProgress = () => (
    <div className="space-y-4">
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          {uploadProgress?.status === 'uploading' && (
            <Loader className="w-6 h-6 text-primary-600 animate-spin" />
          )}
          {uploadProgress?.status === 'processing' && (
            <Loader className="w-6 h-6 text-primary-600 animate-spin" />
          )}
          {uploadProgress?.status === 'complete' && (
            <CheckCircle className="w-6 h-6 text-green-600" />
          )}
          {uploadProgress?.status === 'error' && (
            <AlertCircle className="w-6 h-6 text-red-600" />
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-medium text-gray-900 truncate">
            {uploadProgress?.fileName}
          </h3>
          <p className="text-sm text-gray-500">
            {uploadProgress?.status === 'uploading' && '正在上传...'}
            {uploadProgress?.status === 'processing' && '正在处理...'}
            {uploadProgress?.status === 'complete' && '上传完成！'}
            {uploadProgress?.status === 'error' && uploadProgress.error}
          </p>
        </div>
      </div>
      
      {uploadProgress?.status !== 'error' && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">进度</span>
            <span className="text-gray-900 font-medium">
              {uploadProgress?.progress || 0}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress?.progress || 0}%` }}
            />
          </div>
        </div>
      )}
      
      {uploadProgress?.status === 'error' && (
        <button
          onClick={() => {
            setUploadProgress(null);
            setSelectedFile(null);
          }}
          className="btn-secondary w-full"
        >
          重新选择文件
        </button>
      )}
    </div>
  );

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleModalClick}
    >
      <div className="bg-white rounded-xl shadow-elegant-lg max-w-md w-full max-h-screen overflow-y-auto animate-scale-in">
        {/* 模态框头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            上传 PSD 模板
          </h2>
          <button
            onClick={handleCancel}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 模态框内容 */}
        <div className="p-6">
          {uploadProgress ? (
            renderUploadProgress()
          ) : selectedFile ? (
            renderFilePreview()
          ) : (
            renderUploadZone()
          )}
        </div>
      </div>
    </div>
  );
};