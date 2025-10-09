import React from 'react';
import { AlertCircle, X } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText = '确定',
  cancelText = '取消',
  onConfirm,
  onCancel
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[60] flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 relative">
        {/* 关闭按钮 */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 p-1.5 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>

        <div className="flex items-start pr-8">
          <AlertCircle className="w-6 h-6 text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
            <p className="text-sm text-gray-600 whitespace-pre-line">{message}</p>
          </div>
        </div>
        <div className="mt-6 flex items-center justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 text-gray-700 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-colors"
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};
