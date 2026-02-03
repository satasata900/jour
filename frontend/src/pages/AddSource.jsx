import React, { useState, useEffect } from 'react';
import { ArrowRight, MessageCircle, Send, Globe, Loader2, Check, Plus } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const PlatformCard = ({ title, description, icon: Icon, iconColor, selected, onClick }) => (
    <button
        onClick={onClick}
        className={cn(
            "p-6 rounded-2xl border text-right transition-all w-full",
            selected
                ? "border-primary bg-primary/10 ring-2 ring-primary/50"
                : "border-white/5 bg-surface/40 hover:bg-surface/60 hover:border-white/10"
        )}
    >
        <div className="flex items-start gap-4">
            <div className={cn("p-3 rounded-xl", iconColor)}>
                <Icon className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
                <h3 className="font-bold text-neutral-100">{title}</h3>
                <p className="text-sm text-neutral-500 mt-1">{description}</p>
            </div>
            {selected && (
                <div className="p-1 rounded-full bg-primary text-white">
                    <Check className="h-4 w-4" />
                </div>
            )}
        </div>
    </button>
);

export default function AddSource() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [platform, setPlatform] = useState(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    // Form data
    const [formData, setFormData] = useState({
        name: '',
        url: '',
        labels: []
    });

    // Telegram channels from backend
    const [telegramChannels, setTelegramChannels] = useState([]);
    const [loadingChannels, setLoadingChannels] = useState(false);
    const [selectedChannels, setSelectedChannels] = useState([]);

    // Fetch telegram channels when platform is selected
    const fetchTelegramChannels = async () => {
        setLoadingChannels(true);
        try {
            // This endpoint should return available telegram groups/channels
            const res = await fetch('/api/telegram/channels');
            if (res.ok) {
                const data = await res.json();
                setTelegramChannels(Array.isArray(data) ? data : []);
            }
        } catch (err) {
            console.error("Failed to fetch telegram channels", err);
        } finally {
            setLoadingChannels(false);
        }
    };

    useEffect(() => {
        if (platform === 'telegram') {
            fetchTelegramChannels();
        }
    }, [platform]);

    const handleSubmit = async () => {
        setSaving(true);
        setError('');

        try {
            // For telegram, we might add multiple sources
            if (platform === 'telegram' && selectedChannels.length > 0) {
                for (const channel of selectedChannels) {
                    await fetch('/api/sources', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: channel.title || channel.name,
                            type: 'telegram',
                            url: channel.id || channel.username,
                            active: true,
                            labels: []
                        })
                    });
                }
            } else {
                // Single source (RSS or WhatsApp)
                const res = await fetch('/api/sources', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: formData.name,
                        type: platform,
                        url: formData.url,
                        active: true,
                        labels: []
                    })
                });

                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || 'Failed to create source');
                }
            }

            navigate('/sources');
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const toggleChannel = (channel) => {
        setSelectedChannels(prev => {
            const exists = prev.find(c => c.id === channel.id);
            if (exists) {
                return prev.filter(c => c.id !== channel.id);
            }
            return [...prev, channel];
        });
    };

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-8">
                <Link to="/sources" className="inline-flex items-center gap-2 text-neutral-400 hover:text-white text-sm mb-4 transition-colors">
                    <ArrowRight className="h-4 w-4" />
                    العودة للمصادر
                </Link>
                <h2 className="text-2xl font-bold text-neutral-100">إضافة مصدر جديد</h2>
                <p className="text-sm text-neutral-500 mt-1">اختر نوع المصدر وأدخل التفاصيل</p>
            </div>

            {/* Step Indicator */}
            <div className="flex items-center gap-4 mb-8">
                <div className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold",
                    step >= 1 ? "bg-primary text-white" : "bg-white/10 text-neutral-500"
                )}>1</div>
                <div className={cn("flex-1 h-1 rounded", step >= 2 ? "bg-primary" : "bg-white/10")} />
                <div className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold",
                    step >= 2 ? "bg-primary text-white" : "bg-white/10 text-neutral-500"
                )}>2</div>
            </div>

            {/* Step 1: Choose Platform */}
            {step === 1 && (
                <div className="space-y-6">
                    <h3 className="text-lg font-bold text-neutral-200">اختر نوع المصدر</h3>
                    <div className="grid gap-4 md:grid-cols-3">
                        <PlatformCard
                            title="واتساب"
                            description="ربط مجموعات واتساب لجمع الرسائل"
                            icon={MessageCircle}
                            iconColor="bg-emerald-500"
                            selected={platform === 'whatsapp'}
                            onClick={() => setPlatform('whatsapp')}
                        />
                        <PlatformCard
                            title="تليغرام"
                            description="ربط قنوات ومجموعات تليغرام"
                            icon={Send}
                            iconColor="bg-sky-500"
                            selected={platform === 'telegram'}
                            onClick={() => setPlatform('telegram')}
                        />
                        <PlatformCard
                            title="RSS Feed"
                            description="إضافة روابط RSS لمواقع الأخبار"
                            icon={Globe}
                            iconColor="bg-amber-500"
                            selected={platform === 'rss'}
                            onClick={() => setPlatform('rss')}
                        />
                    </div>

                    <div className="flex justify-end">
                        <button
                            onClick={() => setStep(2)}
                            disabled={!platform}
                            className="px-6 py-2.5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            التالي
                        </button>
                    </div>
                </div>
            )}

            {/* Step 2: Details */}
            {step === 2 && (
                <div className="space-y-6">
                    <h3 className="text-lg font-bold text-neutral-200">
                        {platform === 'telegram' ? 'اختر القنوات' : 'تفاصيل المصدر'}
                    </h3>

                    {/* Telegram: Show available channels */}
                    {platform === 'telegram' && (
                        <div className="space-y-4">
                            {loadingChannels ? (
                                <div className="flex items-center justify-center py-12">
                                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                    <span className="mr-3 text-neutral-400">جاري جلب القنوات...</span>
                                </div>
                            ) : telegramChannels.length > 0 ? (
                                <div className="grid gap-3 max-h-96 overflow-y-auto p-1">
                                    {telegramChannels.map((channel) => (
                                        <button
                                            key={channel.id}
                                            onClick={() => toggleChannel(channel)}
                                            className={cn(
                                                "flex items-center gap-4 p-4 rounded-xl border transition-all text-right",
                                                selectedChannels.find(c => c.id === channel.id)
                                                    ? "border-primary bg-primary/10"
                                                    : "border-white/5 bg-surface/40 hover:bg-surface/60"
                                            )}
                                        >
                                            <div className="flex-1">
                                                <p className="font-medium text-neutral-200">{channel.title || channel.name}</p>
                                                <p className="text-xs text-neutral-500">@{channel.username || channel.id}</p>
                                            </div>
                                            {selectedChannels.find(c => c.id === channel.id) && (
                                                <Check className="h-5 w-5 text-primary" />
                                            )}
                                        </button>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12 text-neutral-500 border border-dashed border-white/10 rounded-xl">
                                    <p>لم يتم العثور على قنوات</p>
                                    <p className="text-sm mt-2">تأكد من ربط حساب تليغرام في الإعدادات</p>
                                </div>
                            )}
                            <p className="text-sm text-neutral-500">
                                تم اختيار {selectedChannels.length} قناة
                            </p>
                        </div>
                    )}

                    {/* WhatsApp & RSS: Manual form */}
                    {(platform === 'whatsapp' || platform === 'rss') && (
                        <div className="space-y-4 max-w-lg">
                            <div>
                                <label className="text-sm font-medium text-neutral-400 block mb-2">اسم المصدر</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
                                    placeholder={platform === 'rss' ? 'مثال: BBC Arabic' : 'مثال: مجموعة الأخبار'}
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium text-neutral-400 block mb-2">
                                    {platform === 'rss' ? 'رابط RSS' : 'معرف المجموعة'}
                                </label>
                                <input
                                    type="text"
                                    value={formData.url}
                                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono text-sm"
                                    placeholder={platform === 'rss' ? 'https://example.com/feed.xml' : 'Group ID'}
                                    dir="ltr"
                                />
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-between">
                        <button
                            onClick={() => setStep(1)}
                            className="px-6 py-2.5 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors font-medium"
                        >
                            السابق
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={saving || (platform === 'telegram' ? selectedChannels.length === 0 : !formData.name || !formData.url)}
                            className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                        >
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                            إضافة المصدر
                        </button>
                    </div>
                </div>
            )}
        </DashboardLayout>
    );
}
