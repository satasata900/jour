import React, { useState, useEffect, useCallback } from 'react';
import { Save, Key, Globe, Shield, Bell, Loader2, Cpu, Check, RefreshCw, Sparkles } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

// Known Gemini models with their required API versions
const GEMINI_MODELS = [
    { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', description: 'أسرع وأحدث', apiVersion: 'v1beta' },
    { id: 'gemini-2.0-flash-lite', name: 'Gemini 2.0 Flash Lite', description: 'خفيف وسريع', apiVersion: 'v1beta' },
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', description: 'سريع ومتوازن', apiVersion: 'v1beta' },
    { id: 'gemini-1.5-flash-8b', name: 'Gemini 1.5 Flash 8B', description: 'خفيف جداً', apiVersion: 'v1beta' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', description: 'أقوى وأذكى', apiVersion: 'v1beta' },
    { id: 'gemini-1.0-pro', name: 'Gemini 1.0 Pro', description: 'مستقر وموثوق', apiVersion: 'v1' },
];

const SettingSection = ({ title, icon: Icon, children }) => (
    <div className="rounded-xl border border-white/5 bg-surface/40 p-6 backdrop-blur-sm">
        <div className="flex items-center gap-3 mb-6 border-b border-white/5 pb-4">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <Icon className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-bold text-neutral-100">{title}</h3>
        </div>
        <div className="space-y-4">
            {children}
        </div>
    </div>
);

const InputField = ({ label, type = "text", placeholder, value, onChange, dir = "rtl" }) => (
    <div className="space-y-1.5">
        <label className="text-sm font-medium text-neutral-400">{label}</label>
        <input
            type={type}
            className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
            placeholder={placeholder}
            value={value === null || value === undefined ? '' : value}
            onChange={onChange}
            dir={dir}
        />
    </div>
);

export default function Settings() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [config, setConfig] = useState(null);

    // OpenRouter models state
    const [openrouterModels, setOpenrouterModels] = useState([]);
    const [loadingModels, setLoadingModels] = useState(false);
    const [modelsError, setModelsError] = useState('');
    const [showFreeOnly, setShowFreeOnly] = useState(false);

    const fetchSettings = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/settings');
            if (res.ok) {
                const data = await res.json();
                setConfig(data);
            }
        } catch (err) {
            console.error("Failed to fetch settings", err);
        } finally {
            setLoading(false);
        }
    };

    const fetchOpenRouterModels = useCallback(async () => {
        const apiKey = config?.keys?.openrouter_api_key;
        if (!apiKey) {
            setOpenrouterModels([]);
            return;
        }

        setLoadingModels(true);
        setModelsError('');
        try {
            const res = await fetch('/api/settings/openrouter/models', {
                headers: {
                    'X-OpenRouter-Key': apiKey
                }
            });
            if (res.ok) {
                const data = await res.json();
                setOpenrouterModels(data.models || []);
            } else {
                const errData = await res.json();
                setModelsError(errData.detail || 'فشل في جلب المودلز');
            }
        } catch (err) {
            setModelsError('فشل في الاتصال');
        } finally {
            setLoadingModels(false);
        }
    }, [config?.keys?.openrouter_api_key]);

    const handleSave = async () => {
        if (!config) return;
        setSaving(true);

        // Log what we're saving for debugging
        console.log("Saving settings:", JSON.stringify(config, null, 2));

        try {
            const res = await fetch('/api/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            if (res.ok) {
                const saved = await res.json();
                console.log("Settings saved successfully:", saved);
                alert("تم حفظ الإعدادات بنجاح");
            } else {
                const errData = await res.json();
                console.error("Save error:", errData);
                alert("حدث خطأ: " + (errData.detail || JSON.stringify(errData)));
            }
        } catch (err) {
            console.error("Failed to save settings", err);
            alert("فشل الاتصال بالخادم");
        } finally {
            setSaving(false);
        }
    };

    const updateConfig = (section, field, value) => {
        setConfig(prev => {
            if (!prev) return prev;
            return {
                ...prev,
                [section]: {
                    ...(prev[section] || {}),
                    [field]: value
                }
            };
        });
    };

    // Update Gemini model and automatically set correct API version
    const updateGeminiModel = (modelId) => {
        const model = GEMINI_MODELS.find(m => m.id === modelId);
        const apiVersion = model?.apiVersion || 'v1beta';

        setConfig(prev => {
            if (!prev) return prev;
            return {
                ...prev,
                ai: {
                    ...(prev.ai || {}),
                    agent_llm_model: modelId,
                    gemini_api_version: apiVersion
                }
            };
        });
    };

    useEffect(() => {
        fetchSettings();
    }, []);

    // Fetch OpenRouter models when provider is openrouter and key exists
    useEffect(() => {
        if (config?.ai?.agent_llm_provider === 'openrouter' && config?.keys?.openrouter_api_key) {
            fetchOpenRouterModels();
        }
    }, [config?.ai?.agent_llm_provider, config?.keys?.openrouter_api_key, fetchOpenRouterModels]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex h-screen items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            </DashboardLayout>
        );
    }

    const getVal = (section, field) => config?.[section]?.[field];
    const currentProvider = getVal('ai', 'agent_llm_provider') || 'openrouter';

    // Filter OpenRouter models
    const filteredOpenRouterModels = showFreeOnly
        ? openrouterModels.filter(m => m.is_free)
        : openrouterModels;
    const freeCount = openrouterModels.filter(m => m.is_free).length;

    return (
        <DashboardLayout>
            <div className="mb-8 flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-neutral-100 to-neutral-400 bg-clip-text text-transparent">
                        الإعدادات
                    </h2>
                    <p className="text-sm text-neutral-500">تهيئة النظام ومفاتيح الربط</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-6 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors text-sm font-bold shadow-lg shadow-primary/20 disabled:opacity-50"
                >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    حفظ التغييرات
                </button>
            </div>

            <div className="space-y-6">
                {/* AI Provider & Model Selection */}
                <SettingSection title="مزود الذكاء الاصطناعي" icon={Cpu}>
                    {/* Provider Selection */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-neutral-400">المزود الافتراضي</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => updateConfig('ai', 'agent_llm_provider', 'gemini')}
                                className={cn(
                                    "p-4 rounded-xl border text-right transition-all flex items-center gap-3",
                                    currentProvider === 'gemini'
                                        ? "border-primary bg-primary/10 ring-1 ring-primary/50"
                                        : "border-white/5 bg-white/5 hover:bg-white/10"
                                )}
                            >
                                <Sparkles className={cn("h-6 w-6", currentProvider === 'gemini' ? "text-primary" : "text-neutral-500")} />
                                <div>
                                    <p className="font-bold text-neutral-200">Google Gemini</p>
                                    <p className="text-xs text-neutral-500">مودلز جوجل</p>
                                </div>
                                {currentProvider === 'gemini' && <Check className="h-5 w-5 text-primary mr-auto" />}
                            </button>
                            <button
                                type="button"
                                onClick={() => updateConfig('ai', 'agent_llm_provider', 'openrouter')}
                                className={cn(
                                    "p-4 rounded-xl border text-right transition-all flex items-center gap-3",
                                    currentProvider === 'openrouter'
                                        ? "border-primary bg-primary/10 ring-1 ring-primary/50"
                                        : "border-white/5 bg-white/5 hover:bg-white/10"
                                )}
                            >
                                <Globe className={cn("h-6 w-6", currentProvider === 'openrouter' ? "text-primary" : "text-neutral-500")} />
                                <div>
                                    <p className="font-bold text-neutral-200">OpenRouter</p>
                                    <p className="text-xs text-neutral-500">مودلز متعددة + مجانية</p>
                                </div>
                                {currentProvider === 'openrouter' && <Check className="h-5 w-5 text-primary mr-auto" />}
                            </button>
                        </div>
                    </div>

                    {/* Gemini Model Selection */}
                    {currentProvider === 'gemini' && (
                        <div className="space-y-2 pt-4 border-t border-white/5">
                            <label className="text-sm font-medium text-neutral-400">مودل Gemini</label>
                            <select
                                value={getVal('ai', 'agent_llm_model') || 'gemini-2.0-flash'}
                                onChange={(e) => updateGeminiModel(e.target.value)}
                                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 focus:border-primary/50 focus:outline-none"
                            >
                                {GEMINI_MODELS.map(model => (
                                    <option key={model.id} value={model.id}>
                                        {model.name} - {model.description} ({model.apiVersion})
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-neutral-500">
                                نسخة API: {GEMINI_MODELS.find(m => m.id === getVal('ai', 'agent_llm_model'))?.apiVersion || 'v1beta'}
                            </p>
                        </div>
                    )}

                    {/* OpenRouter Model Selection */}
                    {currentProvider === 'openrouter' && (
                        <div className="space-y-3 pt-4 border-t border-white/5">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-neutral-400">مودل OpenRouter</label>
                                <div className="flex items-center gap-3">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={showFreeOnly}
                                            onChange={(e) => setShowFreeOnly(e.target.checked)}
                                            className="rounded border-white/20 bg-black/20 text-primary focus:ring-primary/50"
                                        />
                                        <span className="text-xs text-emerald-400">المجاني فقط ({freeCount})</span>
                                    </label>
                                    <button
                                        onClick={fetchOpenRouterModels}
                                        disabled={loadingModels}
                                        className="p-1.5 rounded-lg bg-white/5 text-neutral-400 hover:bg-white/10"
                                    >
                                        <RefreshCw className={cn("h-4 w-4", loadingModels && "animate-spin")} />
                                    </button>
                                </div>
                            </div>

                            {modelsError && (
                                <p className="text-xs text-red-400">{modelsError}</p>
                            )}

                            {loadingModels ? (
                                <div className="flex items-center justify-center py-4">
                                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                                </div>
                            ) : filteredOpenRouterModels.length > 0 ? (
                                <select
                                    value={getVal('ai', 'agent_llm_model') || 'openrouter/auto'}
                                    onChange={(e) => updateConfig('ai', 'agent_llm_model', e.target.value)}
                                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 focus:border-primary/50 focus:outline-none"
                                >
                                    <option value="openrouter/auto">تلقائي (Auto)</option>
                                    {filteredOpenRouterModels.map(model => (
                                        <option key={model.id} value={model.id}>
                                            {model.is_free ? '🆓 ' : ''}{model.name}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <p className="text-xs text-neutral-500">أدخل مفتاح OpenRouter لجلب المودلز</p>
                            )}

                            <p className="text-xs text-neutral-500">
                                {openrouterModels.length} مودل متاح • {freeCount} مجاني
                            </p>
                        </div>
                    )}
                </SettingSection>

                {/* Current Settings Summary */}
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <h4 className="text-sm font-bold text-emerald-400 mb-2">الإعدادات الحالية</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div>
                            <span className="text-neutral-500">المزود: </span>
                            <span className="text-neutral-200 font-medium">{currentProvider === 'gemini' ? 'Gemini' : 'OpenRouter'}</span>
                        </div>
                        <div>
                            <span className="text-neutral-500">المودل: </span>
                            <span className="text-neutral-200 font-medium font-mono">{getVal('ai', 'agent_llm_model') || 'غير محدد'}</span>
                        </div>
                        <div>
                            <span className="text-neutral-500">API Version: </span>
                            <span className="text-neutral-200 font-medium font-mono">{getVal('ai', 'gemini_api_version') || 'v1beta'}</span>
                        </div>
                        <div>
                            <span className="text-neutral-500">مفتاح Gemini: </span>
                            <span className={getVal('keys', 'gemini_api_key') ? "text-emerald-400" : "text-red-400"}>
                                {getVal('keys', 'gemini_api_key') ? '✓ موجود' : '✗ مفقود'}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                    {/* API Keys */}
                    <SettingSection title="مفاتيح الذكاء الاصطناعي" icon={Key}>
                        <InputField
                            label="Google Gemini API Key"
                            type="password"
                            placeholder="AIzaSy..."
                            value={getVal('keys', 'gemini_api_key')}
                            onChange={(e) => updateConfig('keys', 'gemini_api_key', e.target.value)}
                            dir="ltr"
                        />
                        <InputField
                            label="OpenRouter API Key"
                            type="password"
                            placeholder="sk-or-..."
                            value={getVal('keys', 'openrouter_api_key')}
                            onChange={(e) => updateConfig('keys', 'openrouter_api_key', e.target.value)}
                            dir="ltr"
                        />
                        <div className="text-xs text-neutral-500 mt-2 bg-amber-500/5 p-3 rounded-lg border border-amber-500/10 text-amber-500/80">
                            تنبيه: هذه المفاتيح تستخدم لتشغيل وكلاء التحليل والتلخيص. يرجى الحفاظ على سريتها.
                        </div>
                    </SettingSection>

                    {/* System Config */}
                    <SettingSection title="إعدادات النظام" icon={Shield}>
                        <div className="grid grid-cols-2 gap-4">
                            <InputField
                                label="مدة الاحتفاظ بالأخبار (أيام)"
                                type="number"
                                value={getVal('retention', 'days')}
                                onChange={(e) => updateConfig('retention', 'days', Number(e.target.value))}
                            />
                            <InputField
                                label="فاصل التحديث (ثانية)"
                                type="number"
                                value={getVal('ai', 'summary_run_interval_seconds')}
                                onChange={(e) => updateConfig('ai', 'summary_run_interval_seconds', Number(e.target.value))}
                            />
                        </div>

                        <div className="pt-4 border-t border-white/5 space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-neutral-300">تفعيل Telegram</span>
                                <input
                                    type="checkbox"
                                    checked={getVal('telegram', 'enabled') || false}
                                    onChange={(e) => updateConfig('telegram', 'enabled', e.target.checked)}
                                    className="accent-primary h-5 w-5"
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-neutral-300">تفعيل Whatsapp</span>
                                <input
                                    type="checkbox"
                                    checked={getVal('whatsapp', 'enabled') || false}
                                    onChange={(e) => updateConfig('whatsapp', 'enabled', e.target.checked)}
                                    className="accent-primary h-5 w-5"
                                />
                            </div>
                        </div>
                    </SettingSection>
                </div>
            </div>
        </DashboardLayout>
    );
}
