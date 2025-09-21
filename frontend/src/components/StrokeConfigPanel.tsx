import React, { useState, useCallback } from 'react';
import { Plus, X, AlertTriangle } from 'lucide-react';
import { StrokeConfig } from '../types/index.ts';

interface StrokeConfigPanelProps {
  strokeConfigs: StrokeConfig[];
  onStrokeConfigsChange: (configs: StrokeConfig[]) => void;
  maxConfigs?: number;
}

export const StrokeConfigPanel: React.FC<StrokeConfigPanelProps> = ({
  strokeConfigs,
  onStrokeConfigsChange,
  maxConfigs = 5
}) => {
  const [newStrokeWidth, setNewStrokeWidth] = useState<string>('');
  const [validationError, setValidationError] = useState<string>('');

  // 添加新的stroke配置
  const handleAddStroke = useCallback(() => {
    const width = parseInt(newStrokeWidth);

    // 验证输入
    if (isNaN(width) || width < 1 || width > 10) {
      setValidationError('Stroke宽度必须在1-10像素之间');
      return;
    }

    // 检查重复
    if (strokeConfigs.some(config => config.width === width)) {
      setValidationError('该Stroke宽度已存在');
      return;
    }

    // 检查数量限制
    if (strokeConfigs.length >= maxConfigs) {
      setValidationError(`最多只能配置${maxConfigs}个Stroke版本`);
      return;
    }

    // 添加新配置
    const newConfig: StrokeConfig = {
      width,
      color: '#FFFFFF',
      enabled: true
    };

    const updatedConfigs = [...strokeConfigs, newConfig].sort((a, b) => a.width - b.width);
    onStrokeConfigsChange(updatedConfigs);

    // 重置输入
    setNewStrokeWidth('');
    setValidationError('');
  }, [newStrokeWidth, strokeConfigs, maxConfigs, onStrokeConfigsChange]);

  // 删除stroke配置
  const handleRemoveStroke = useCallback((index: number) => {
    const updatedConfigs = strokeConfigs.filter((_, i) => i !== index);
    onStrokeConfigsChange(updatedConfigs);
  }, [strokeConfigs, onStrokeConfigsChange]);

  // 切换启用状态
  const handleToggleEnabled = useCallback((index: number) => {
    const updatedConfigs = strokeConfigs.map((config, i) =>
      i === index ? { ...config, enabled: !config.enabled } : config
    );
    onStrokeConfigsChange(updatedConfigs);
  }, [strokeConfigs, onStrokeConfigsChange]);

  // 获取启用的stroke宽度数组
  const getEnabledWidths = useCallback(() => {
    return strokeConfigs
      .filter(config => config.enabled)
      .map(config => config.width)
      .sort((a, b) => a - b);
  }, [strokeConfigs]);

  const enabledWidths = getEnabledWidths();

  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Stroke版本配置</h3>
        <span className="text-xs text-gray-500">
          {strokeConfigs.length}/{maxConfigs} 已配置
        </span>
      </div>

      {/* 配置列表 */}
      {strokeConfigs.length > 0 && (
        <div className="space-y-2">
          {strokeConfigs.map((config, index) => (
            <div
              key={config.width}
              className={`flex items-center justify-between p-3 rounded-md border transition-colors ${
                config.enabled
                  ? 'bg-white border-blue-200 shadow-sm'
                  : 'bg-gray-100 border-gray-200'
              }`}
            >
              <div className="flex items-center space-x-3">
                <label className="inline-flex items-center cursor-pointer select-none relative">
                  <input
                    type="checkbox"
                    checked={config.enabled}
                    onChange={() => handleToggleEnabled(index)}
                    className="peer appearance-none w-4 h-4 rounded border border-gray-300 bg-gray-50 transition focus:outline-none focus:ring-2 focus:ring-gray-300"
                  />
                  <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 rounded bg-primary-600 opacity-0 peer-checked:opacity-100" />
                  <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 flex items-center justify-center opacity-0 peer-checked:opacity-100 z-10">
                    <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M5 13l4 4L19 7" className="text-white" />
                    </svg>
                  </span>
                </label>
                <span className={`text-sm font-medium ${
                  config.enabled ? 'text-gray-900' : 'text-gray-500'
                }`}>
                  {config.width}px Stroke
                </span>
              </div>

              <button
                onClick={() => handleRemoveStroke(index)}
                className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                title="删除配置"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 添加新配置 */}
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <div className="flex-1">
            <input
              type="number"
              min="1"
              max="10"
              value={newStrokeWidth}
              onChange={(e) => {
                setNewStrokeWidth(e.target.value);
                setValidationError('');
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddStroke();
                }
              }}
              placeholder="输入Stroke宽度 (1-10px)"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-gray-50 text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            onClick={handleAddStroke}
            disabled={strokeConfigs.length >= maxConfigs}
            className={`p-2 rounded-md transition-colors ${
              strokeConfigs.length >= maxConfigs
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
            title="添加Stroke配置"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* 验证错误提示 */}
        {validationError && (
          <div className="flex items-center space-x-2 text-sm text-red-600">
            <AlertTriangle className="w-4 h-4" />
            <span>{validationError}</span>
          </div>
        )}
      </div>

      {/* 预览信息 */}
      {enabledWidths.length > 0 && (
        <div className="pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-600">
            <strong>将生成的Stroke版本：</strong>
            <span className="ml-2">
              {enabledWidths.map(width => `${width}px`).join(', ')}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            总计：原始版本 + {enabledWidths.length} 个Stroke版本
          </div>
        </div>
      )}

      {/* 使用说明 */}
      {strokeConfigs.length === 0 && (
        <div className="text-center py-6 text-gray-500">
          <div className="text-sm">暂无Stroke配置</div>
          <div className="text-xs mt-1">
            添加Stroke配置后将生成对应的描边版本模板
          </div>
        </div>
      )}
    </div>
  );
};
