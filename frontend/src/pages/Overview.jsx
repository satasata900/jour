import React, { useEffect, useState } from 'react';
import { Activity, MessageSquare, Newspaper, Zap, Users, RefreshCw, Loader2 } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const StatsCard = ({ title, value, icon: Icon, color, loading }) => (
    <div className="rounded-2xl border border-white/5 bg-surface/40 p-6 backdrop-blur-sm transition-all hover:bg-surface/60 hover:shadow-lg hover:shadow-primary/5">
        <div className="flex items-start justify-between">
            <div>
                <p className="text-sm font-medium text-neutral-400">{title}</p>
                {loading ? (
                    <div className="mt-2 h-9 w-16 bg-white/5 rounded animate-pulse" />
                ) : (
                    <h3 className="mt-2 text-3xl font-bold text-neutral-100">{value}</h3>
                )}
            </div>
            <div className={`rounded-xl p-3 ${color} bg-opacity-10 text-white`}>
                <Icon className="h-6 w-6 opacity-80" />
            </div>
        </div>
    </div>
);

export default function Overview() {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        totalMessages: 0,
        activeSources: 0,
        activeAgents: 0,
        latestTimestamp: null,
        byPlatform: []
    });

    const fetchStats = async () => {
        setLoading(true);
        try {
            // Fetch news stats
            const newsRes = await fetch('/api/news/stats');
            const newsData = newsRes.ok ? await newsRes.json() : {};

            // Fetch sources
            const sourcesRes = await fetch('/api/sources');
            const sourcesData = sourcesRes.ok ? await sourcesRes.json() : [];
            const activeSources = Array.isArray(sourcesData)
                ? sourcesData.filter(s => s.active).length
                : 0;

            // Fetch agents
            const agentsRes = await fetch('/api/agents');
            const agentsData = agentsRes.ok ? await agentsRes.json() : [];
            const activeAgents = Array.isArray(agentsData)
                ? agentsData.filter(a => a.is_active).length
                : 0;

            setStats({
                totalMessages: newsData?.total || 0,
                activeSources: activeSources,
                activeAgents: activeAgents,
                latestTimestamp: newsData?.latest_timestamp || null,
                byPlatform: newsData?.by_platform || []
            });
        } catch (err) {
            console.error("Failed to fetch stats", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    // Format the latest timestamp
    const formatDate = (timestamp) => {
        if (!timestamp) return 'غير متوفر';
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return 'غير متوفر';
        return date.toLocaleString('ar-SA', {
            dateStyle: 'medium',
            timeStyle: 'short'
        });
    };

    return (
        <DashboardLayout>
            <div className="mb-8 flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-neutral-100">نظرة عامة</h2>
                    <p className="text-neutral-400 mt-2">ملخص النشاط وحالة النظام</p>
                </div>
                <button
                    onClick={fetchStats}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-xl hover:bg-primary/20 transition-colors text-sm font-medium disabled:opacity-50"
                >
                    <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    تحديث
                </button>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                    title="إجمالي الرسائل"
                    value={stats.totalMessages.toLocaleString()}
                    icon={MessageSquare}
                    color="bg-blue-500"
                    loading={loading}
                />
                <StatsCard
                    title="المصادر النشطة"
                    value={stats.activeSources}
                    icon={Newspaper}
                    color="bg-emerald-500"
                    loading={loading}
                />
                <StatsCard
                    title="الوكلاء النشطين"
                    value={stats.activeAgents}
                    icon={Zap}
                    color="bg-purple-500"
                    loading={loading}
                />
                <StatsCard
                    title="آخر تحديث"
                    value={formatDate(stats.latestTimestamp)}
                    icon={Activity}
                    color="bg-amber-500"
                    loading={loading}
                />
            </div>

            {/* Platform Breakdown */}
            {stats.byPlatform.length > 0 && (
                <div className="mt-8">
                    <h3 className="text-lg font-bold text-neutral-200 mb-4">توزيع الرسائل حسب المنصة</h3>
                    <div className="grid gap-4 sm:grid-cols-3">
                        {stats.byPlatform.map((item) => (
                            <div key={item.platform} className="rounded-xl border border-white/5 bg-surface/30 p-4 flex items-center justify-between">
                                <span className="text-neutral-300 capitalize">{item.platform}</span>
                                <span className="text-xl font-bold text-primary">{item.count?.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="mt-8 grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6 h-64 flex items-center justify-center text-neutral-500">
                    مخطط بياني للنشاط (Coming Soon)
                </div>
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6 h-64 flex items-center justify-center text-neutral-500">
                    آخر التنبيهات (Coming Soon)
                </div>
            </div>
        </DashboardLayout>
    );
}
