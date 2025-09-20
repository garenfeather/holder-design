import React, { useEffect, useState } from 'react';
import { X, Download, Trash2, ImageIcon, FileIcon, AlertCircle } from 'lucide-react';
import { Result, ResultDetail } from '../types/index.ts';
import { apiService, API_BASE_URL } from '../services/api.ts';

interface ResultDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: Result | null;
  onDeleted?: (id: string) => void;
}

export const ResultDetailModal: React.FC<ResultDetailModalProps> = ({
  isOpen,
  onClose,
  result,
  onDeleted,
}) => {
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<ResultDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!isOpen || !result) {
      setInfo(null);
      setError(null);
      return;
    }
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiService.getResultInfo(result.id);
        if (res.success && res.data) {
          setInfo(res.data);
        } else {
          setError(res.error || '加载详情失败');
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isOpen, result?.id]);

  if (!isOpen || !result) return null;

  const download = async () => {
    if (!result) return;
    try {
      await apiService.downloadFile(result.id, `${result.templateName}_${result.id}.psd`);
    } catch (e) {
      setError(e instanceof Error ? e.message : '下载失败');
    }
  };

  const handleDelete = async () => {
    if (!result) return;
    if (!confirm('确定删除该生成结果吗？此操作不可撤销。')) return;
    setDeleting(true);
    setError(null);
    const res = await apiService.deleteResult(result.id);
    setDeleting(false);
    if (res.success) {
      onDeleted?.(result.id);
      onClose();
    } else {
      setError(res.error || '删除失败');
    }
  };

  const createdAtText = result.createdAt ? new Date(result.createdAt).toLocaleString() : '';

  const previewSrc = info?.previewUrl
    ? `${API_BASE_URL}${info.previewUrl}`
    : `${API_BASE_URL}/api/results/${result.id}/preview`;

  return (
    <div className="fixed inset-0 bg-white/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-elegant-xl max-w-4xl w-full max-h-[90vh] mx-4 flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">生成结果详情</h2>
            <p className="text-sm text-gray-500 mt-1 break-all">{result.templateName} · #{result.id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-auto p-6 space-y-4">
          {error && (
            <div className="flex items-start p-3 border border-red-200 bg-red-50 text-red-700 rounded-lg">
              <AlertCircle className="w-4 h-4 mt-0.5 mr-2" />
              <div className="text-sm">{error}</div>
            </div>
          )}

          {loading ? (
            <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
          ) : (
            <>
              {/* 预览：复用生成结果预览样式（灰底 + 自适应宽高） */}
              <div className="w-full rounded p-2 md:p-3" style={{ backgroundColor: 'rgb(128,128,128)' }}>
                {info?.previewExists ? (
                  <img src={previewSrc} alt="预览图" className="w-full h-auto" />
                ) : (
                  <div className="text-gray-400 text-sm flex flex-col items-center py-16 bg-white rounded">
                    <ImageIcon className="w-10 h-10 mb-2" />
                    无预览图
                  </div>
                )}
              </div>

              {/* 基本信息：放到预览图下方 */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-2">基本信息</h3>
                <div className="border border-gray-200 rounded-lg divide-y">
                  <div className="p-3 text-sm text-gray-700">模板名称：{result.templateName}</div>
                  <div className="p-3 text-sm text-gray-700">创建时间：{createdAtText}</div>
                  {info?.usedStrokeWidth !== undefined && (
                    <div className="p-3 text-sm text-gray-700">使用模板：{info?.usedStrokeWidth ? `Stroke ${info.usedStrokeWidth}px` : '原始'}</div>
                  )}
                  <div className="p-3 text-sm text-gray-700 flex items-center">
                    <FileIcon className="w-4 h-4 mr-2 text-gray-500" />
                    PSD文件：{info?.psdExists ? (
                      <span className="text-green-600">可下载{info?.finalPsdSize ? ` · ${(info.finalPsdSize / 1024 / 1024).toFixed(1)} MB` : ''}</span>
                    ) : (
                      <span className="text-gray-500">不存在</span>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex items-center space-x-3">
                  <button
                    onClick={download}
                    disabled={!info?.psdExists}
                    className={`inline-flex items-center px-3 py-1.5 text-sm rounded-lg transition-colors focus:outline-none ${
                      info?.psdExists ? 'bg-primary-600 hover:bg-primary-700 text-white focus:ring-2 focus:ring-primary-300 focus:ring-offset-1' : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    }`}
                  >
                    <Download className="w-4 h-4 mr-2" /> 下载PSD
                  </button>

                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className={`inline-flex items-center px-3 py-1.5 text-sm rounded-lg border transition-colors focus:outline-none ${
                      deleting ? 'bg-gray-100 text-gray-600 border-gray-200 cursor-wait' : 'bg-white hover:bg-red-50 text-red-600 border-red-200 focus:ring-2 focus:ring-red-300 focus:ring-offset-1'
                    }`}
                  >
                    <Trash2 className="w-4 h-4 mr-2" /> 删除
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
