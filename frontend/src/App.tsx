import React, { useState, useEffect } from 'react';
import { Upload, Package, Wifi, WifiOff } from 'lucide-react';
import { TemplateBox } from './components/TemplateBox.tsx';
import { ResultsBox } from './components/ResultsBox.tsx';
import { UploadModal } from './components/UploadModal.tsx';
import { PreviewModal } from './components/PreviewModal.tsx';
import { DieElementList } from './components/DieElementList.tsx';
import { DieMaterialAndLayoutManager } from './components/DieMaterialAndLayoutManager.tsx';
import { PrintLayout } from './components/PrintLayout.tsx';
import { Template } from './types/index.ts';
import { apiService } from './services/api.ts';
import { appConfig } from './config.ts';

function App() {
  const [isServerOnline, setIsServerOnline] = useState<boolean | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  // Tab状态
  const [activeTab, setActiveTab] = useState<'templates' | 'results' | 'elements' | 'materials' | 'layout'>('templates');

  // 打印排版相关状态
  const [loadTemplateId, setLoadTemplateId] = useState<string | null>(null);
  const [printMaterialCreated, setPrintMaterialCreated] = useState(0);

  const backendAddress = `${appConfig.domain}:8012`;

  useEffect(() => {
    checkServerStatus();
    // 每30秒检查一次服务器状态
    const interval = setInterval(checkServerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkServerStatus = async () => {
    const online = await apiService.healthCheck();
    setIsServerOnline(online);
  };

  const handleUploadSuccess = (templateId: string) => {
    // 上传成功后触发模板列表刷新
    setRefreshCounter(prev => prev + 1);
    console.log('Upload success:', templateId);
  };

  const handleUploadError = (error: string) => {
    // 可以添加错误提示
    console.error('Upload error:', error);
  };

  const handleTemplateSelect = (template: Template) => {
    setSelectedTemplate(template);
    // 这里可以实现模板使用逻辑
    console.log('Selected template:', template);
  };

  const handleTemplatePreview = (template: Template) => {
    setPreviewTemplate(template);
    setIsPreviewModalOpen(true);
  };

  const renderServerStatus = () => (
    <div className={`
      flex items-center space-x-2 px-3 py-1.5 rounded-full text-sm font-medium
      ${isServerOnline === true
        ? 'bg-green-100 text-green-700'
        : isServerOnline === false
        ? 'bg-red-100 text-red-700'
        : 'bg-yellow-100 text-yellow-700'
      }
    `}>
      {isServerOnline === true && <Wifi className="w-4 h-4" />}
      {isServerOnline === false && <WifiOff className="w-4 h-4" />}
      {isServerOnline === null && <div className="w-4 h-4 bg-yellow-500 rounded-full animate-pulse" />}

      <span>
        {isServerOnline === true && '服务器在线'}
        {isServerOnline === false && '服务器离线'}
        {isServerOnline === null && '检查中...'}
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo 和标题 */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">🎨</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    PSD Template Manager
                  </h1>
                  <p className="text-xs text-gray-500 -mt-0.5">
                    优雅的模板管理工具
                  </p>
                </div>
              </div>
            </div>

            {/* 服务器状态 */}
            <div className="flex items-center space-x-4">
              {renderServerStatus()}
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab导航 - 两组并列显示 */}
        <div className="mb-6 flex justify-center items-center gap-6">
          {/* 第一组: 异形模版箱子 和 生成素材管理 */}
          <div className="inline-flex bg-white border border-gray-200 rounded-lg p-0.5">
            <button
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'templates' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveTab('templates')}
            >
              异形模版箱子
            </button>
            <button
              className={`ml-0.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'results' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveTab('results')}
            >
              生成素材管理
            </button>
          </div>

          {/* 分隔符 */}
          <div className="w-px h-8 bg-gray-300"></div>

          {/* 第二组: 刀模相关三个tab */}
          <div className="inline-flex bg-white border border-gray-200 rounded-lg p-0.5">
            <button
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'elements' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveTab('elements')}
            >
              刀模元素管理
            </button>
            <button
              className={`ml-0.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'materials' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveTab('materials')}
            >
              刀模素材与排版管理
            </button>
            <button
              className={`ml-0.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'layout' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveTab('layout')}
            >
              打印排版
            </button>
          </div>
        </div>

        {isServerOnline === false && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl animate-fade-in">
            <div className="flex items-center">
              <WifiOff className="w-5 h-5 text-red-600 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">
                  服务器连接失败
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  无法连接到后端服务器 ({backendAddress})。请确保服务器正在运行。
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 页面内容 */}
        <div className="animate-fade-in">
          {activeTab === 'templates' && (
            <TemplateBox
              onCreateNew={() => setIsUploadModalOpen(true)}
              onTemplateSelect={handleTemplateSelect}
              onTemplatePreview={handleTemplatePreview}
              refreshTrigger={refreshCounter}
            />
          )}
          {activeTab === 'results' && <ResultsBox />}
          {activeTab === 'elements' && <DieElementList />}
          {activeTab === 'materials' && (
            <DieMaterialAndLayoutManager
              onUseTemplate={(templateId) => {
                setLoadTemplateId(templateId);
                setActiveTab('layout');
              }}
              onPrintMaterialCreated={() => setPrintMaterialCreated(prev => prev + 1)}
            />
          )}
          {activeTab === 'layout' && (
            <PrintLayout
              loadTemplateId={loadTemplateId}
              onTemplateLoaded={() => setLoadTemplateId(null)}
              onPrintMaterialCreated={() => {
                setPrintMaterialCreated(prev => prev + 1);
                alert('打印素材生成成功！可前往"刀模素材与排版管理"页面查看');
              }}
            />
          )}
        </div>
      </main>

      {/* 页脚 */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>PSD Template Manager v1.0.0</p>
            <p className="mt-1">优雅 • 简洁 • 现代化的模板管理工具</p>
          </div>
        </div>
      </footer>

      {/* 上传模态框（仅异形模版箱子Tab使用） */}
      {activeTab === 'templates' && (
        <UploadModal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          onUploadSuccess={handleUploadSuccess}
          onUploadError={handleUploadError}
        />
      )}

      {/* 预览模态框（仅异形模版箱子Tab使用） */}
      {activeTab === 'templates' && (
        <PreviewModal
          isOpen={isPreviewModalOpen}
          onClose={() => setIsPreviewModalOpen(false)}
          template={previewTemplate}
        />
      )}
    </div>
  );
}

export default App;
