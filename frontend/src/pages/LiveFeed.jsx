import React, { useEffect, useState, useCallback } from 'react';
import { MessageCircle, Send, Globe, RefreshCw, Loader2, Filter, Clock, Search, ExternalLink } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const MessageCard = ({ message }) => {
    const formatTime = (timestamp) => {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return '';
        return date.toLocaleString('ar-SA', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-transparent hover:border-white/10 group">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-primary truncate max-w-[60%]">
                    {message.source_name || 'مصدر غير معروف'}
                </span>
                <span className="text-xs text-neutral-500 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatTime(message.timestamp)}
                </span>
            </div>

            {/* Content */}
            <p className="text-sm text-neutral-300 line-clamp-4 leading-relaxed">
                {message.clean_content || message.content || ''}
            </p>

            {/* Footer */}
            {message.author_name && (
                <p className="text-xs text-neutral-500 mt-2 truncate">
                    من: {message.author_name}
                </p>
            )}
        </div>
    );
};

const PlatformColumn = ({ title, icon: Icon, iconColor, messages, loading }) => (
    <div className="flex flex-col rounded-2xl border border-white/5 bg-surface/30 backdrop-blur-sm overflow-hidden">
        {/* Column Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5 bg-surface/50">
            <div className="flex items-center gap-3">
                <div className={cn("p-2 rounded-lg", iconColor)}>
                    <Icon className="h-5 w-5 text-white" />
                </div>
                <div>
                    <h3 className="font-bold text-neutral-100">{title}</h3>
                    <p className="text-xs text-neutral-500">{messages.length} رسالة</p>
                </div>
            </div>
        </div>

        {/* Scrollable Message List */}
        <div className="flex-1 overflow-y-auto max-h-[600px] p-3 space-y-3">
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
            ) : messages.length === 0 ? (
                <div className="text-center py-12 text-neutral-500 text-sm">
                    لا توجد رسائل
                </div>
            ) : (
                messages.map((msg) => (
                    <MessageCard key={msg.id} message={msg} />
                ))
            )}
        </div>
    </div>
);

export default function LiveFeed() {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [showActiveOnly, setShowActiveOnly] = useState(true);
    const [autoRefresh, setAutoRefresh] = useState(true);

    const fetchMessages = useCallback(async () => {
        try {
            // active_only=true is default in backend, but we can explicitly set it
            const params = new URLSearchParams({
                limit: '100',
                active_only: showActiveOnly ? 'true' : 'false'
            });

            const res = await fetch(`/api/news?${params}`);
            if (!res.ok) {
                throw new Error(`Failed to fetch: ${res.status}`);
            }
            const data = await res.json();
            console.log("Fetched messages:", data?.length || 0);
            setMessages(Array.isArray(data) ? data : []);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch messages", err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [showActiveOnly]);

    useEffect(() => {
        fetchMessages();
    }, [fetchMessages]);

    // Auto-refresh every 30 seconds
    useEffect(() => {
        if (!autoRefresh) return;
        const interval = setInterval(() => {
            fetchMessages();
        }, 30000);
        return () => clearInterval(interval);
    }, [autoRefresh, fetchMessages]);

    // Filter messages by search
    const filteredMessages = messages.filter(msg => {
        if (!searchQuery) return true;
        const content = (msg.content || msg.clean_content || '').toLowerCase();
        const source = (msg.source_name || '').toLowerCase();
        const query = searchQuery.toLowerCase();
        return content.includes(query) || source.includes(query);
    });

    // Group by platform
    const whatsappMessages = filteredMessages.filter(m => m.platform === 'whatsapp');
    const telegramMessages = filteredMessages.filter(m => m.platform === 'telegram');
    const rssMessages = filteredMessages.filter(m => m.platform === 'rss');

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-500 bg-clip-text text-transparent">
                        البث المباشر
                    </h2>
                    <p className="text-sm text-neutral-500">
                        آخر الرسائل من المصادر النشطة
                        {autoRefresh && <span className="text-emerald-500 mr-2">• تحديث تلقائي</span>}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setAutoRefresh(!autoRefresh)}
                        className={cn(
                            "px-3 py-2 rounded-xl text-xs font-medium transition-all border",
                            autoRefresh
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-white/5 text-neutral-400 border-white/10"
                        )}
                    >
                        {autoRefresh ? "إيقاف التحديث" : "تفعيل التحديث"}
                    </button>
                    <button
                        onClick={() => { setLoading(true); fetchMessages(); }}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors text-sm font-medium border border-white/10"
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                        تحديث الآن
                    </button>
                </div>
            </div>

            {/* Search & Filters */}
            <div className="mb-6 flex flex-col md:flex-row gap-4">
                {/* Search */}
                <div className="relative flex-1">
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                    <input
                        type="text"
                        placeholder="ابحث في الرسائل..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pr-10 pl-4 py-2.5 rounded-xl border border-white/10 bg-black/20 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/50 text-sm"
                    />
                </div>

                {/* Active Only Filter */}
                <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showActiveOnly}
                            onChange={(e) => setShowActiveOnly(e.target.checked)}
                            className="rounded border-white/20 bg-black/20 text-primary focus:ring-primary/50"
                        />
                        <span className="text-sm text-neutral-400">فقط المصادر النشطة</span>
                    </label>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                    خطأ في جلب البيانات: {error}
                </div>
            )}

            {/* Stats Bar */}
            <div className="mb-6 flex items-center gap-4 text-xs text-neutral-500">
                <span>الإجمالي: {filteredMessages.length}</span>
                <span>•</span>
                <span>واتساب: {whatsappMessages.length}</span>
                <span>•</span>
                <span>تليغرام: {telegramMessages.length}</span>
                <span>•</span>
                <span>RSS: {rssMessages.length}</span>
            </div>

            {/* Three Column Layout */}
            <div className="grid gap-6 lg:grid-cols-3">
                <PlatformColumn
                    title="واتساب"
                    icon={MessageCircle}
                    iconColor="bg-emerald-500"
                    messages={whatsappMessages}
                    loading={loading}
                />
                <PlatformColumn
                    title="تليغرام"
                    icon={Send}
                    iconColor="bg-sky-500"
                    messages={telegramMessages}
                    loading={loading}
                />
                <PlatformColumn
                    title="RSS"
                    icon={Globe}
                    iconColor="bg-amber-500"
                    messages={rssMessages}
                    loading={loading}
                />
            </div>
        </DashboardLayout>
    );
}
