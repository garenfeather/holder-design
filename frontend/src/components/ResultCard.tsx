import React from 'react';
import { Calendar, Eye, Trash2 } from 'lucide-react';
import { Result } from '../types/index.ts';

interface ResultCardProps {
  result: Result;
  className?: string;
  onView?: (r: Result) => void;
  onDelete?: (r: Result) => void;
  selectable?: boolean;
  selected?: boolean;
  onSelectChange?: (r: Result, selected: boolean) => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({ result, className = '', onView, onDelete, selectable = false, selected = false, onSelectChange }) => {
  const createdAtText = result.createdAt
    ? new Date(result.createdAt).toLocaleString()
    : '';

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-4 ${className}`}>
      
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            {result.templateName}
          </h3>
          <p className="text-xs text-gray-500 mt-1 break-all">#{result.id}</p>
        </div>
        {selectable && (
          <label className="ml-2 inline-flex items-center cursor-pointer select-none relative">
            <input
              type="checkbox"
              className="peer appearance-none w-4 h-4 rounded border border-gray-300 bg-white transition focus:outline-none focus:ring-2 focus:ring-gray-300"
              checked={selected}
              onChange={(e) => onSelectChange?.(result, e.target.checked)}
            />
            <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 rounded bg-primary-600 opacity-0 peer-checked:opacity-100" />
            <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 flex items-center justify-center opacity-0 peer-checked:opacity-100 z-10">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="3">
                <path d="M5 13l4 4L19 7" className="text-white" />
              </svg>
            </span>
          </label>
        )}
      </div>

      <div className="mt-4 flex items-center text-sm text-gray-600">
        <Calendar className="w-4 h-4 mr-2 text-gray-500" />
        <span>创建时间：{createdAtText}</span>
      </div>

      <div className="mt-4 flex items-center space-x-2">
        <button
          onClick={() => onView?.(result)}
          className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-1 active:scale-95 transition"
        >
          <Eye className="w-4 h-4 mr-2" /> 详情
        </button>
        <button
          onClick={() => onDelete?.(result)}
          className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-300 focus:ring-offset-1 active:scale-95 transition"
        >
          <Trash2 className="w-4 h-4 mr-2" /> 删除
        </button>
      </div>
    </div>
  );
};
