import React, { useState, useEffect } from 'react';
import { FileText, Calendar, CalendarDays, CalendarRange, Loader2, RefreshCw, Clock, ChevronDown, ChevronUp, Timer, Trash2 } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const PERIOD_TYPES = [
    { key: 'interval', label: 'نصف ساعية', icon: Timer, color: 'amber' },
    { key: 'daily', label: 'يومية', icon: Calendar, color: 'emerald' },
    { key: 'weekly', label: 'أسبوعية', icon: CalendarDays, color: 'blue' },
    { key: 'monthly', label: 'شهرية', icon: CalendarRange, color: 'purple' },
];

const SummaryCard = ({ summary, expanded, onToggle, onDeleteLine, saving }) => {
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('ar-SA', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getTypeColor = (type) => {
        switch (type) {
            case 'interval': return 'amber';
            case 'daily': return 'emerald';
            case 'weekly': return 'blue';
            case 'monthly': return 'purple';
            default: return 'neutral';
        }
    };

    const color = getTypeColor(summary.period_type);

    const lines = (summary.content || '').split(/\r?\n/);

    return (
        <div className={cn(
            "rounded-xl border transition-all duration-300",
            expanded ? `border-${color}-500/30 bg-${color}-500/5` : "border-white/5 bg-surface/40"
        )}>
            {/* Header */}
            <button
                onClick={onToggle}
                className="w-full flex items-center justify-between p-4 text-right hover:bg-white/5 transition-colors rounded-t-xl"
            >
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "p-2 rounded-lg",
                        `bg-${color}-500/10 text-${color}-400`
                    )}>
                        <Clock className="h-4 w-4" />
                    </div>
                    <div>
                        <p className="font-medium text-neutral-200">
                            {formatDate(summary.period_start)}
                            <span className="text-neutral-500 mx-2">←</span>
                            {formatDate(summary.period_end)}
                        </p>
                        <p className="text-xs text-neutral-500">
                            {summary.period_type === 'interval' && 'ملخص ساعي'}
                            {summary.period_type === 'daily' && 'ملخص يومي'}
                            {summary.period_type === 'weekly' && 'ملخص أسبوعي'}
                            {summary.period_type === 'monthly' && 'ملخص شهري'}
                        </p>
                    </div>
                </div>
                {expanded ? (
                    <ChevronUp className="h-5 w-5 text-neutral-500" />
                ) : (
                    <ChevronDown className="h-5 w-5 text-neutral-500" />
                )}
            </button>

            {/* Content */}
            {expanded && (
                <div className="p-4 pt-0 border-t border-white/5">
                    <div className="prose prose-invert prose-sm max-w-none">
                        {lines.length === 0 ? (
                            <div className="text-neutral-300 leading-relaxed whitespace-pre-wrap text-sm" dir="rtl">
                                لا يوجد محتوى
                            </div>
                        ) : (
                            <div className="space-y-1" dir="rtl">
                                {lines.map((line, index) => (
                                    <div key={`${summary.id}-${index}`} className="group flex items-start gap-2">
                                        <button
                                            type="button"
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                onDeleteLine(summary.id, index);
                                            }}
                                            disabled={saving}
                                            className={cn(
                                                "mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-md border border-white/10 text-neutral-400 transition-colors",
                                                saving
                                                    ? "cursor-not-allowed opacity-50"
                                                    : "hover:text-red-400 hover:border-red-500/40 hover:bg-red-500/10"
                                            )}
                                            title="حذف السطر"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                        <div className="text-neutral-300 leading-relaxed whitespace-pre-wrap text-sm flex-1">
                                            {line.trim().length === 0 ? "\u00A0" : line}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default function Summaries() {
    const [activeTab, setActiveTab] = useState('daily');
    const [summaries, setSummaries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState(null);
    const [savingId, setSavingId] = useState(null);
    const [stats, setStats] = useState({
        interval: 0,
        daily: 0,
        weekly: 0,
        monthly: 0
    });

    // Fetch counts for all period types from database
    const fetchStats = async () => {
        try {
            const res = await fetch('/api/summaries/stats');
            if (res.ok) {
                const data = await res.json();
                console.log("Stats from DB:", data);
                setStats(data);
            }
        } catch (err) {
            console.error("Failed to fetch stats", err);
        }
    };

    const fetchSummaries = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/summaries?period_type=${activeTab}&limit=20`);
            if (res.ok) {
                const data = await res.json();
                setSummaries(data);
                // Update stats for active tab
                setStats(prev => ({ ...prev, [activeTab]: data.length >= 20 ? prev[activeTab] : data.length }));
                // Auto-expand the first one
                if (data.length > 0) {
                    setExpandedId(data[0].id);
                }
            }
        } catch (err) {
            console.error("Failed to fetch summaries", err);
        } finally {
            setLoading(false);
        }
    };

    const normalizeContent = (lines) => {
        const trimmed = lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
        return trimmed.length === 0 ? "" : trimmed;
    };

    const updateSummaryContent = async (summaryId, content) => {
        setSavingId(summaryId);
        try {
            const res = await fetch(`/api/summaries/${summaryId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (res.ok) {
                const updated = await res.json();
                setSummaries(prev => prev.map(item => item.id === summaryId ? updated : item));
            }
        } catch (err) {
            console.error("Failed to update summary", err);
        } finally {
            setSavingId(null);
        }
    };

    const handleDeleteLine = (summaryId, lineIndex) => {
        const summary = summaries.find(item => item.id === summaryId);
        if (!summary || !summary.content) {
            return;
        }
        const lines = summary.content.split(/\r?\n/);
        if (lineIndex < 0 || lineIndex >= lines.length) {
            return;
        }
        lines.splice(lineIndex, 1);
        const updated = normalizeContent(lines);
        if (!updated) {
            return;
        }
        updateSummaryContent(summaryId, updated);
    };

    // Fetch stats on mount
    useEffect(() => {
        fetchStats();
    }, []);

    useEffect(() => {
        fetchSummaries();
    }, [activeTab]);

    const activeConfig = PERIOD_TYPES.find(p => p.key === activeTab);

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                        الملخصات
                    </h2>
                    <p className="text-sm text-neutral-500">ملخصات الأخبار اليومية والأسبوعية والشهرية</p>
                </div>
                <button
                    onClick={fetchSummaries}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors text-sm font-medium border border-white/10"
                >
                    <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    تحديث
                </button>
            </div>

            {/* Stats - Clickable cards that also filter */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {PERIOD_TYPES.map((period) => {
                    const Icon = period.icon;
                    const count = stats[period.key] || 0;
                    const isActive = activeTab === period.key;
                    return (
                        <button
                            key={period.key}
                            onClick={() => setActiveTab(period.key)}
                            className={cn(
                                "rounded-xl p-4 border transition-all text-right",
                                isActive
                                    ? `border-${period.color}-500/30 bg-${period.color}-500/10`
                                    : "border-white/5 bg-surface/40 hover:bg-white/5"
                            )}
                        >
                            <div className="flex items-center gap-3">
                                <div className={cn(
                                    "p-2 rounded-lg",
                                    `bg-${period.color}-500/20 text-${period.color}-400`
                                )}>
                                    <Icon className="h-5 w-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-bold text-neutral-100">{count}</p>
                                    <p className="text-xs text-neutral-500">{period.label}</p>
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Tabs - Alternative filter */}
            <div className="flex gap-2 mb-6 p-1 bg-surface/40 rounded-xl border border-white/5 w-fit">
                {PERIOD_TYPES.map((period) => {
                    const Icon = period.icon;
                    const isActive = activeTab === period.key;
                    return (
                        <button
                            key={period.key}
                            onClick={() => setActiveTab(period.key)}
                            className={cn(
                                "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                                isActive
                                    ? `bg-${period.color}-500/20 text-${period.color}-400 shadow-lg shadow-${period.color}-500/10`
                                    : "text-neutral-400 hover:text-neutral-200 hover:bg-white/5"
                            )}
                        >
                            <Icon className="h-4 w-4" />
                            {period.label}
                        </button>
                    );
                })}
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : summaries.length === 0 ? (
                <div className="text-center py-20">
                    <FileText className="h-16 w-16 text-neutral-700 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-neutral-400 mb-2">لا توجد ملخصات</h3>
                    <p className="text-sm text-neutral-500">
                        لم يتم إنشاء ملخصات {activeConfig?.label} بعد
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {summaries.map((summary) => (
                        <SummaryCard
                            key={summary.id}
                            summary={summary}
                            expanded={expandedId === summary.id}
                            onToggle={() => setExpandedId(expandedId === summary.id ? null : summary.id)}
                            onDeleteLine={handleDeleteLine}
                            saving={savingId === summary.id}
                        />
                    ))}
                </div>
            )}
        </DashboardLayout>
    );
}
