import React, { useEffect, useMemo, useState } from 'react';
import { RefreshCw, Package, AlertCircle, CheckCircle2, ChevronDown, Trash2, Filter, ArrowUpDown, ShieldQuestion } from 'lucide-react';
import { Result } from '../types/index.ts';
import { apiService } from '../services/api.ts';
import { ResultCard } from './ResultCard.tsx';
import { ResultDetailModal } from './ResultDetailModal.tsx';

interface ResultsBoxProps {
  className?: string;
}

export const ResultsBox: React.FC<ResultsBoxProps> = ({ className = '' }) => {
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [selected, setSelected] = useState<Result | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [query, setQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getResults();
      if (res.success && res.data) {
        // 按创建时间倒序
        const sorted = [...res.data].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        setResults(sorted);
        setSelectedIds(new Set());
        setSelectAll(false);
      } else {
        setError(res.error || '加载结果失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredResults = useMemo(() => {
    const byQuery = query.trim().toLowerCase();
    let arr = results.filter(r => !byQuery || r.templateName.toLowerCase().includes(byQuery));
    arr = arr.sort((a, b) => {
      const t = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      return sortOrder === 'asc' ? t : -t;
    });
    return arr;
  }, [results, query, sortOrder]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await loadResults();
    } finally {
      setRefreshing(false);
    }
  };

  const onView = (r: Result) => {
    setSelected(r);
    setDetailOpen(true);
  };

  const onDelete = async (r: Result) => {
    if (!confirm('确定要删除该生成结果吗？此操作不可撤销。')) return;
    setError(null);
    const res = await apiService.deleteResult(r.id);
    if (res.success) {
      setSuccess('删除成功');
      setResults(prev => prev.filter(x => x.id !== r.id));
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(r.id);
        return next;
      });
      setTimeout(() => setSuccess(null), 2000);
    } else {
      setError(res.error || '删除失败');
    }
  };

  const renderEmpty = () => (
    <div className="text-center py-12">
      <div className="mx-auto w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
        <Package className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-gray-900">暂无生成结果</h3>
      <p className="mt-1 text-sm text-gray-500">完成一次生成后，这里会展示结果列表。</p>
    </div>
  );

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-900">生成素材管理</h2>
        <div className="flex items-center space-x-2">
          <div className="hidden sm:flex items-center group border border-gray-200 border-l-gray-200 focus-within:border-primary-400 focus-within:border-l-gray-200 hover:border-primary-300 rounded-lg overflow-hidden bg-white shadow-sm focus-within:shadow transition-colors">
            <Filter className="w-4 h-4 mx-2 text-gray-400 group-focus-within:text-primary-500 transition-colors" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="按模板名筛选"
              className="px-3 py-1.5 text-sm text-gray-800 placeholder-gray-400 bg-transparent border-0 focus:outline-none focus:ring-0 rounded-none"
            />
          </div>

          <button
            onClick={() => setSortOrder(p => (p === 'desc' ? 'asc' : 'desc'))}
            title="切换排序"
            className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg border bg-white hover:bg-gray-50 text-gray-700 border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-1 active:scale-95 transition"
          >
            <ArrowUpDown className="w-4 h-4 mr-2" />
            {sortOrder === 'desc' ? '新→旧' : '旧→新'}
          </button>

          <button
            onClick={refresh}
            className={`inline-flex items-center px-3 py-1.5 text-sm rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-1 active:scale-95 transition ${
              refreshing ? 'bg-gray-100 text-gray-600 border-gray-200 cursor-wait' : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200'
            }`}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* 批量操作栏 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <label className="inline-flex items-center space-x-2 text-sm text-gray-700">
            <span className="relative inline-flex">
              <input
                type="checkbox"
                className="peer appearance-none w-4 h-4 rounded border border-gray-300 bg-white transition focus:outline-none focus:ring-2 focus:ring-gray-300"
                checked={selectAll}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSelectAll(checked);
                  if (checked) {
                    setSelectedIds(new Set(filteredResults.map(r => r.id)));
                  } else {
                    setSelectedIds(new Set());
                  }
                }}
              />
              <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 rounded bg-primary-600 opacity-0 peer-checked:opacity-100" />
              <span className="pointer-events-none absolute left-0 top-0 w-4 h-4 flex items-center justify-center opacity-0 peer-checked:opacity-100 z-10">
                <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M5 13l4 4L19 7" className="text-white" />
                </svg>
              </span>
            </span>
            <span>全选（当前筛选）</span>
          </label>

          <span className="text-xs text-gray-500">已选 {selectedIds.size} 条</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={async () => {
              if (selectedIds.size === 0) return;
              if (!confirm(`删除所选 ${selectedIds.size} 条结果？此操作不可撤销。`)) return;
              const ids = Array.from(selectedIds);
              const outcome = await apiService.deleteResultsBulk(ids);
              if (outcome.ok.length) {
                setResults(prev => prev.filter(x => !outcome.ok.includes(x.id)));
                setSuccess(`已删除 ${outcome.ok.length} 条`);
                setTimeout(() => setSuccess(null), 2000);
              }
              if (outcome.failed.length) {
                setError(`删除失败 ${outcome.failed.length} 条`);
              }
              setSelectedIds(new Set());
              setSelectAll(false);
            }}
            className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-300 focus:ring-offset-1 active:scale-95 transition"
          >
            <Trash2 className="w-4 h-4 mr-2" /> 删除所选
          </button>

          <button
            onClick={async () => {
              const keep = window.prompt('清理旧结果：保留最近 N 条（留空则跳过）', '100');
              const days = window.prompt('同时删除超过 X 天的结果（留空则跳过）', '');
              const keepRecent = keep && !isNaN(parseInt(keep)) ? parseInt(keep) : undefined;
              const olderThanDays = days && !isNaN(parseInt(days)) ? parseInt(days) : undefined;
              const res = await apiService.cleanupResults({ keepRecent, olderThanDays });
              if (res.success && res.data) {
                // 直接刷新列表
                await loadResults();
                setSuccess('清理完成');
                setTimeout(() => setSuccess(null), 2000);
              } else {
                setError(res.error || '清理失败');
              }
            }}
            className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg border bg-white hover:bg-gray-50 text-gray-700 border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-1 active:scale-95 transition"
            title="按数量和天数自动清理"
          >
            <ChevronDown className="w-4 h-4 mr-2" /> 清理旧结果
          </button>
        </div>
      </div>

      {/* 全局消息 */}
      {error && (
        <div className="mb-4 flex items-start p-3 border border-red-200 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="w-4 h-4 mt-0.5 mr-2" />
          <div className="text-sm">{error}</div>
        </div>
      )}
      {success && (
        <div className="mb-4 flex items-start p-3 border border-green-200 bg-green-50 text-green-700 rounded-lg">
          <CheckCircle2 className="w-4 h-4 mt-0.5 mr-2" />
          <div className="text-sm">{success}</div>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="h-24 bg-white rounded-xl border border-gray-200 animate-pulse" />
          ))}
        </div>
      ) : results.length === 0 ? (
        renderEmpty()
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResults.map((r) => (
            <ResultCard
              key={r.id}
              result={r}
              onView={onView}
              onDelete={onDelete}
              selectable
              selected={selectedIds.has(r.id)}
              onSelectChange={(_, checked) => {
                setSelectedIds(prev => {
                  const next = new Set(prev);
                  if (checked) next.add(r.id); else next.delete(r.id);
                  return next;
                });
              }}
            />
          ))}
        </div>
      )}

      <ResultDetailModal
        isOpen={detailOpen}
        onClose={() => setDetailOpen(false)}
        result={selected}
        onDeleted={(id) => {
          setResults(prev => prev.filter(x => x.id !== id));
          setSuccess('删除成功');
          setTimeout(() => setSuccess(null), 2000);
        }}
      />
    </div>
  );
};
