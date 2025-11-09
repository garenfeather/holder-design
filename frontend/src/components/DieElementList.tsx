import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Scissors, X } from 'lucide-react';
import { apiService } from '../services/api.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { DieElementEditor } from './DieElementEditor.tsx';

interface DieElement {
  id: string;
  name: string;
  cutSize: {
    width: number;
    height: number;
  };
  referenceSize: {
    width: number;
    height: number;
  };
  createdAt: string;
  updatedAt: string;
}

interface ElementFormData {
  name: string;
  cutWidth: string;
  cutHeight: string;
  refWidth: string;
  refHeight: string;
}

export const DieElementList: React.FC = () => {
  const [elements, setElements] = useState<DieElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingElement, setEditingElement] = useState<DieElement | null>(null);
  const [formData, setFormData] = useState<ElementFormData>({
    name: '',
    cutWidth: '',
    cutHeight: '',
    refWidth: '',
    refHeight: '',
  });
  const [formError, setFormError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; element: DieElement | null }>({
    show: false,
    element: null,
  });
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedElement, setSelectedElement] = useState<DieElement | null>(null);

  // 加载元素列表
  const loadElements = async () => {
    setLoading(true);
    try {
      const response = await apiService.getDieElements();
      if (response.success && response.data) {
        setElements(response.data);
      }
    } catch (error) {
      console.error('加载刀模元素列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadElements();
  }, []);

  // 打开创建模态框
  const handleCreate = () => {
    setEditingElement(null);
    setFormData({
      name: '',
      cutWidth: '',
      cutHeight: '',
      refWidth: '',
      refHeight: '',
    });
    setFormError('');
    setIsModalOpen(true);
  };

  // 打开编辑模态框
  const handleEdit = (element: DieElement) => {
    setEditingElement(element);
    setFormData({
      name: element.name,
      cutWidth: element.cutSize.width.toString(),
      cutHeight: element.cutSize.height.toString(),
      refWidth: element.referenceSize.width.toString(),
      refHeight: element.referenceSize.height.toString(),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  // 表单验证
  const validateForm = (): boolean => {
    if (!formData.name.trim()) {
      setFormError('请输入元素名称');
      return false;
    }

    const cutWidth = parseFloat(formData.cutWidth);
    const cutHeight = parseFloat(formData.cutHeight);
    const refWidth = parseFloat(formData.refWidth);
    const refHeight = parseFloat(formData.refHeight);

    if (isNaN(cutWidth) || cutWidth <= 0) {
      setFormError('裁切宽度必须是大于0的数字');
      return false;
    }
    if (isNaN(cutHeight) || cutHeight <= 0) {
      setFormError('裁切高度必须是大于0的数字');
      return false;
    }
    if (isNaN(refWidth) || refWidth <= 0) {
      setFormError('参考宽度必须是大于0的数字');
      return false;
    }
    if (isNaN(refHeight) || refHeight <= 0) {
      setFormError('参考高度必须是大于0的数字');
      return false;
    }

    setFormError('');
    return true;
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const data = {
      name: formData.name.trim(),
      cutSize: {
        width: parseFloat(formData.cutWidth),
        height: parseFloat(formData.cutHeight),
      },
      referenceSize: {
        width: parseFloat(formData.refWidth),
        height: parseFloat(formData.refHeight),
      },
    };

    try {
      if (editingElement) {
        // 更新
        const response = await apiService.updateDieElement(editingElement.id, data);
        if (response.success) {
          await loadElements();
          setIsModalOpen(false);
        } else {
          setFormError(response.error || '更新失败');
        }
      } else {
        // 创建
        const response = await apiService.createDieElement(data);
        if (response.success) {
          await loadElements();
          setIsModalOpen(false);
        } else {
          setFormError(response.error || '创建失败');
        }
      }
    } catch (error) {
      setFormError('操作失败，请重试');
    }
  };

  // 删除元素
  const handleDelete = (element: DieElement) => {
    setDeleteConfirm({ show: true, element });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm.element) return;

    try {
      const response = await apiService.deleteDieElement(deleteConfirm.element.id);
      if (response.success) {
        await loadElements();
      }
    } catch (error) {
      console.error('删除失败:', error);
    } finally {
      setDeleteConfirm({ show: false, element: null });
    }
  };

  // 打开素材编辑器
  const handleGenerateMaterial = (element: DieElement) => {
    setSelectedElement(element);
    setEditorOpen(true);
  };

  // 素材生成成功后刷新列表
  const handleEditorSuccess = async () => {
    await loadElements();
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">刀模元素管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            创建和管理刀模元素，生成刀模素材
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>创建元素</span>
        </button>
      </div>

      {/* 元素列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-gray-500">加载中...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {elements.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <Scissors className="w-16 h-16 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                还没有刀模元素
              </h3>
              <p className="text-gray-500">
                点击右上角"创建元素"按钮,创建你的第一个刀模元素
              </p>
            </div>
          ) : (
            elements.map((element) => (
              <div
                key={element.id}
                className="border border-gray-200 rounded-xl p-4 hover:shadow-lg transition-shadow"
              >
                <div className="space-y-1">
                  <h3 className="font-semibold text-gray-900 text-sm">{element.name}</h3>
                  <div className="text-xs text-gray-600">
                    <div>裁切: {element.cutSize.width}×{element.cutSize.height}cm</div>
                    <div>参考: {element.referenceSize.width}×{element.referenceSize.height}cm</div>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="mt-3 flex items-center space-x-1">
                  <button
                    onClick={() => handleGenerateMaterial(element)}
                    className="flex-1 px-2 py-1.5 bg-primary-50 text-primary-600 rounded-lg hover:bg-primary-100 transition-colors text-xs font-medium"
                  >
                    生成素材
                  </button>
                  <button
                    onClick={() => handleEdit(element)}
                    className="p-1 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleDelete(element)}
                    className="p-1 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 创建/编辑模态框 */}
      {isModalOpen && (
        <div
          className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setIsModalOpen(false);
            }
          }}
        >
          <div className="bg-white rounded-xl shadow-elegant-lg max-w-md w-full max-h-screen overflow-y-auto animate-scale-in">
            {/* 模态框头部 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                {editingElement ? '编辑元素' : '创建元素'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* 模态框内容 */}
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* 元素名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  元素名称
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="例如: 圆形徽章"
                />
              </div>

              {/* 裁切尺寸 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  裁切尺寸 (cm)
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    step="0.1"
                    value={formData.cutWidth}
                    onChange={(e) => setFormData({ ...formData, cutWidth: e.target.value })}
                    className="px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder="宽度"
                  />
                  <input
                    type="number"
                    step="0.1"
                    value={formData.cutHeight}
                    onChange={(e) => setFormData({ ...formData, cutHeight: e.target.value })}
                    className="px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder="高度"
                  />
                </div>
              </div>

              {/* 参考尺寸 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  参考尺寸 (cm)
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    step="0.1"
                    value={formData.refWidth}
                    onChange={(e) => setFormData({ ...formData, refWidth: e.target.value })}
                    className="px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder="宽度"
                  />
                  <input
                    type="number"
                    step="0.1"
                    value={formData.refHeight}
                    onChange={(e) => setFormData({ ...formData, refHeight: e.target.value })}
                    className="px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder="高度"
                  />
                </div>
              </div>

              {/* 错误提示 */}
              {formError && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {formError}
                </div>
              )}

              {/* 按钮 */}
              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                >
                  {editingElement ? '保存' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      {deleteConfirm.show && deleteConfirm.element && (
        <ConfirmDialog
          isOpen={deleteConfirm.show}
          title="删除刀模元素"
          message={`确定要删除元素"${deleteConfirm.element.name}"吗？此操作将同时删除该元素下的所有素材，且无法恢复。`}
          confirmText="删除"
          cancelText="取消"
          onConfirm={confirmDelete}
          onCancel={() => setDeleteConfirm({ show: false, element: null })}
          type="danger"
        />
      )}

      {/* 刀模素材编辑器 */}
      {editorOpen && selectedElement && (
        <DieElementEditor
          isOpen={editorOpen}
          onClose={() => {
            setEditorOpen(false);
            setSelectedElement(null);
          }}
          elementId={selectedElement.id}
          elementName={selectedElement.name}
          cutSize={selectedElement.cutSize}
          referenceSize={selectedElement.referenceSize}
          onSuccess={handleEditorSuccess}
        />
      )}
    </div>
  );
};
