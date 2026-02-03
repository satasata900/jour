import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Pause, Play, MessageCircle, Send, Globe, RefreshCw, Loader2, Filter } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const PlatformColumn = ({ title, icon: Icon, iconColor, sources, onToggle, onDelete, loading }) => (
    <div className="flex flex-col rounded-2xl border border-white/5 bg-surface/30 backdrop-blur-sm overflow-hidden">
        {/* Column Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5 bg-surface/50">
            <div className="flex items-center gap-3">
                <div className={cn("p-2 rounded-lg", iconColor)}>
                    <Icon className="h-5 w-5 text-white" />
                </div>
                <div>
                    <h3 className="font-bold text-neutral-100">{title}</h3>
                    <p className="text-xs text-neutral-500">{sources.length} مصدر</p>
                </div>
            </div>
        </div>

        {/* Scrollable Source List */}
        <div className="flex-1 overflow-y-auto max-h-[500px] p-3 space-y-2">
            {sources.length === 0 ? (
                <div className="text-center py-8 text-neutral-500 text-sm">
                    لا توجد مصادر
                </div>
            ) : (
                sources.map((source) => (
                    <div
                        key={source.id}
                        className="group flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-transparent hover:border-white/10"
                    >
                        {/* Status Indicator (always visible) */}
                        <div className={cn(
                            "w-2 h-2 rounded-full ml-3 flex-shrink-0",
                            source.is_active ? "bg-emerald-500" : "bg-neutral-600"
                        )} />

                        <div className="flex-1 min-w-0">
                            <p className="font-medium text-neutral-200 text-sm truncate">{source.name}</p>
                            <p className="text-xs text-neutral-500 truncate font-mono">{source.identifier}</p>
                        </div>

                        {/* Actions - Always visible now */}
                        <div className="flex items-center gap-1 mr-2">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onToggle(source);
                                }}
                                disabled={loading === source.id}
                                className={cn(
                                    "p-1.5 rounded-lg transition-colors",
                                    source.is_active
                                        ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                                        : "bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
                                )}
                                title={source.is_active ? "إيقاف مؤقت" : "تشغيل"}
                            >
                                {loading === source.id ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : source.is_active ? (
                                    <Pause className="h-3.5 w-3.5" />
                                ) : (
                                    <Play className="h-3.5 w-3.5" />
                                )}
                            </button>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDelete(source);
                                }}
                                disabled={loading === source.id}
                                className="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                                title="حذف"
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    </div>
                ))
            )}
        </div>
    </div>
);

export default function Sources() {
    const [sources, setSources] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);
    const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'active', 'inactive'

    const fetchSources = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/sources');
            if (res.ok) {
                const data = await res.json();
                console.log("Sources from API:", data);
                setSources(Array.isArray(data) ? data : []);
            } else {
                console.error("Failed to fetch sources:", res.status);
            }
        } catch (err) {
            console.error("Failed to fetch sources", err);
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (source) => {
        const newStatus = !source.is_active;
        console.log("Toggling source:", source.id, "from", source.is_active, "to", newStatus);
        setActionLoading(source.id);
        try {
            const res = await fetch(`/api/sources/${source.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: newStatus })
            });
            console.log("Toggle response status:", res.status);
            if (res.ok) {
                const updated = await res.json();
                console.log("Updated source:", updated);
                setSources(prev => prev.map(s => s.id === source.id ? updated : s));
            } else {
                const errText = await res.text();
                console.error("Toggle failed:", errText);
                alert("فشل في تحديث المصدر: " + errText);
            }
        } catch (err) {
            console.error("Failed to toggle source", err);
            alert("فشل في الاتصال بالخادم");
        } finally {
            setActionLoading(null);
        }
    };

    const handleDelete = async (source) => {
        if (!confirm(`هل أنت متأكد من حذف "${source.name}"؟`)) return;

        console.log("Deleting source:", source.id);
        setActionLoading(source.id);
        try {
            const res = await fetch(`/api/sources/${source.id}`, { method: 'DELETE' });
            console.log("Delete response status:", res.status);
            if (res.ok || res.status === 204) {
                setSources(prev => prev.filter(s => s.id !== source.id));
            } else {
                const errText = await res.text();
                console.error("Delete failed:", errText);
                alert("فشل في حذف المصدر");
            }
        } catch (err) {
            console.error("Failed to delete source", err);
            alert("فشل في الاتصال بالخادم");
        } finally {
            setActionLoading(null);
        }
    };

    useEffect(() => {
        fetchSources();
    }, []);

    // Apply status filter first (using is_active field from backend)
    const filteredSources = sources.filter(s => {
        if (statusFilter === 'active') return s.is_active === true;
        if (statusFilter === 'inactive') return s.is_active === false;
        return true;
    });

    // Group by platform (using platform field from backend)
    const whatsappSources = filteredSources.filter(s => s.platform === 'whatsapp');
    const telegramSources = filteredSources.filter(s => s.platform === 'telegram');
    const rssSources = filteredSources.filter(s => s.platform === 'rss');

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-amber-200 to-yellow-500 bg-clip-text text-transparent">
                        المصادر
                    </h2>
                    <p className="text-sm text-neutral-500">إدارة قنوات التليغرام، الواتساب، وروابط RSS</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={fetchSources}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors text-sm font-medium border border-white/10"
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                        تحديث
                    </button>
                    <Link
                        to="/sources/add"
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors text-sm font-medium shadow-lg shadow-primary/20"
                    >
                        <Plus className="h-4 w-4" />
                        إضافة مصدر
                    </Link>
                </div>
            </div>

            {/* Status Filter */}
            <div className="mb-6 flex items-center gap-3">
                <div className="flex items-center gap-2 text-neutral-400 text-sm">
                    <Filter className="h-4 w-4" />
                    <span>فلترة الحالة:</span>
                </div>
                <div className="flex bg-surface/50 p-1 rounded-xl border border-white/5">
                    {[
                        { value: 'all', label: 'الكل' },
                        { value: 'active', label: 'نشط' },
                        { value: 'inactive', label: 'متوقف' }
                    ].map((option) => (
                        <button
                            key={option.value}
                            onClick={() => setStatusFilter(option.value)}
                            className={cn(
                                "px-4 py-1.5 rounded-lg text-xs font-medium transition-all",
                                statusFilter === option.value
                                    ? "bg-primary/20 text-primary shadow-sm"
                                    : "text-neutral-400 hover:text-neutral-200"
                            )}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
                <span className="text-xs text-neutral-500">
                    ({filteredSources.length} من {sources.length})
                </span>
            </div>

            {/* Loading State */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                /* Three Column Layout */
                <div className="grid gap-6 lg:grid-cols-3">
                    <PlatformColumn
                        title="واتساب"
                        icon={MessageCircle}
                        iconColor="bg-emerald-500"
                        sources={whatsappSources}
                        onToggle={handleToggle}
                        onDelete={handleDelete}
                        loading={actionLoading}
                    />
                    <PlatformColumn
                        title="تليغرام"
                        icon={Send}
                        iconColor="bg-sky-500"
                        sources={telegramSources}
                        onToggle={handleToggle}
                        onDelete={handleDelete}
                        loading={actionLoading}
                    />
                    <PlatformColumn
                        title="RSS"
                        icon={Globe}
                        iconColor="bg-amber-500"
                        sources={rssSources}
                        onToggle={handleToggle}
                        onDelete={handleDelete}
                        loading={actionLoading}
                    />
                </div>
            )}
        </DashboardLayout>
    );
}
