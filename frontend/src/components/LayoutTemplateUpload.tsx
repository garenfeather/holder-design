import React, { useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';

interface Props {
  onUploadSuccess: () => void;
}

interface UnmatchedLayer {
  index: number;
  name: string;
  size: {
    width: number;
    height: number;
  };
}

export const LayoutTemplateUpload: React.FC<Props> = ({ onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showErrorDialog, setShowErrorDialog] = useState(false);
  const [unmatchedLayers, setUnmatchedLayers] = useState<UnmatchedLayer[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 验证文件
    if (!file.name.toLowerCase().endsWith('.psd')) {
      alert('请选择 PSD 文件');
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      alert('文件不能超过 100MB');
      return;
    }

    // 上传
    setUploading(true);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('psd', file);

      const xhr = new XMLHttpRequest();

      // 进度监听
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          setProgress(percentComplete);
        }
      });

      // 完成监听
      xhr.addEventListener('load', () => {
        setUploading(false);
        setProgress(0);

        if (xhr.status === 200) {
          const response = JSON.parse(xhr.responseText);
          if (response.success) {
            alert('上传成功！');
            onUploadSuccess();
          } else {
            // 匹配失败
            if (response.unmatched_layers) {
              setUnmatchedLayers(response.unmatched_layers);
              setShowErrorDialog(true);
            } else {
              alert(response.error || '上传失败');
            }
          }
        } else {
          try {
            const response = JSON.parse(xhr.responseText);
            if (response.unmatched_layers) {
              setUnmatchedLayers(response.unmatched_layers);
              setShowErrorDialog(true);
            } else {
              alert(response.error || '上传失败');
            }
          } catch {
            alert('上传失败');
          }
        }

        // 重置文件输入
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      });

      // 错误监听
      xhr.addEventListener('error', () => {
        setUploading(false);
        setProgress(0);
        alert('上传失败');
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      });

      xhr.open('POST', 'http://localhost:8012/api/layout-templates/upload-psd');
      xhr.send(formData);

    } catch (error) {
      setUploading(false);
      setProgress(0);
      alert('上传失败: ' + (error instanceof Error ? error.message : String(error)));
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <div className="mb-4">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          <Upload size={16} />
          {uploading ? '上传中...' : '上传 PSD 布局模板'}
        </button>

        {uploading && (
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600 mt-1">{progress}%</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".psd"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* 匹配失败错误对话框 */}
      {showErrorDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold text-red-600">❌ 匹配失败</h2>
                <p className="text-sm text-gray-600 mt-1">
                  以下图层无法匹配到刀模元素，请检查 PSD 图层尺寸是否与现有刀模元素一致
                </p>
              </div>
              <button
                onClick={() => setShowErrorDialog(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            <div className="border rounded overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                      图层索引
                    </th>
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                      图层名称
                    </th>
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                      尺寸 (mm)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {unmatchedLayers.map((layer, index) => (
                    <tr
                      key={index}
                      className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                    >
                      <td className="px-4 py-2 text-sm">{layer.index}</td>
                      <td className="px-4 py-2 text-sm">{layer.name}</td>
                      <td className="px-4 py-2 text-sm">
                        {layer.size.width} × {layer.size.height}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowErrorDialog(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
