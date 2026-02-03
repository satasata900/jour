import React, { useState } from 'react';
import { ArrowRight, Bot, Save, Loader2, Info, Zap, Cpu, FileText, Search, Settings } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const AGENT_TYPES = [
    { value: 'router', label: 'موجّه (Router)', icon: Zap, description: 'يوجه المهام للوكلاء المناسبين', requiredFields: ['task', 'context', 'format_instructions'] },
    { value: 'monitor', label: 'مراقب (Monitor)', icon: Cpu, description: 'يراقب البيانات ويولد تقارير', requiredFields: ['window', 'stats'] },
    { value: 'editor', label: 'محرر (Editor)', icon: FileText, description: 'يحرر ويحسن المحتوى', requiredFields: ['task', 'content'] },
    { value: 'search', label: 'باحث (Search)', icon: Search, description: 'يبحث ويجمع المعلومات', requiredFields: ['task'] },
    { value: 'general', label: 'عام (General)', icon: Bot, description: 'وكيل متعدد الاستخدامات', requiredFields: ['task', 'context'] },
    { value: 'custom', label: 'مخصص (Custom)', icon: Settings, description: 'وكيل بإعدادات مخصصة بالكامل', requiredFields: ['task'] },
];

// Generate a unique key from name
const generateKeyFromName = (name) => {
    const base = name
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim()
        .slice(0, 50);

    // Add timestamp suffix to ensure uniqueness
    const suffix = Date.now().toString(36).slice(-4);
    return base ? `${base}-${suffix}` : `agent-${suffix}`;
};

export default function AddAgent() {
    const navigate = useNavigate();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const [formData, setFormData] = useState({
        name: '',
        description: '',
        agent_type: 'general',
        system_prompt: 'You are a helpful AI assistant.',
        user_prompt: 'Task: {task}\n\nContext: {context}',
        is_active: true,
    });

    const selectedType = AGENT_TYPES.find(t => t.value === formData.agent_type);

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        setError('');

        // Generate key automatically from name
        const key = generateKeyFromName(formData.name);
        const payload = { ...formData, key };

        try {
            const res = await fetch('/api/agents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                navigate('/agents');
            } else {
                const data = await res.json();
                setError(data.detail || 'فشل في إنشاء الوكيل');
            }
        } catch (err) {
            setError('فشل في الاتصال بالخادم');
        } finally {
            setSaving(false);
        }
    };

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-8">
                <Link to="/agents" className="inline-flex items-center gap-2 text-neutral-400 hover:text-white text-sm mb-4 transition-colors">
                    <ArrowRight className="h-4 w-4" />
                    العودة للوكلاء
                </Link>
                <h2 className="text-2xl font-bold text-neutral-100">إنشاء وكيل جديد</h2>
                <p className="text-sm text-neutral-500 mt-1">أنشئ وكيل ذكاء اصطناعي مخصص</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6 max-w-4xl">
                {/* Basic Info */}
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6">
                    <h3 className="text-lg font-bold text-neutral-200 mb-4">المعلومات الأساسية</h3>

                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium text-neutral-400 block mb-2">اسم الوكيل *</label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => handleChange('name', e.target.value)}
                                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none"
                                placeholder="مثال: وكيل تحليل الأخبار"
                                required
                            />
                        </div>

                        <div>
                            <label className="text-sm font-medium text-neutral-400 block mb-2">الوصف</label>
                            <input
                                type="text"
                                value={formData.description}
                                onChange={(e) => handleChange('description', e.target.value)}
                                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none"
                                placeholder="وصف مختصر لما يفعله هذا الوكيل"
                            />
                        </div>
                    </div>
                </div>

                {/* Agent Type */}
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6">
                    <h3 className="text-lg font-bold text-neutral-200 mb-4">نوع الوكيل</h3>

                    <div className="grid md:grid-cols-3 gap-3">
                        {AGENT_TYPES.map((type) => {
                            const TypeIcon = type.icon;
                            return (
                                <button
                                    key={type.value}
                                    type="button"
                                    onClick={() => handleChange('agent_type', type.value)}
                                    className={cn(
                                        "p-4 rounded-xl border text-right transition-all",
                                        formData.agent_type === type.value
                                            ? "border-primary bg-primary/10 ring-1 ring-primary/50"
                                            : "border-white/5 bg-white/5 hover:bg-white/10"
                                    )}
                                >
                                    <div className="flex items-start gap-3">
                                        <TypeIcon className={cn(
                                            "h-5 w-5 mt-0.5",
                                            formData.agent_type === type.value ? "text-primary" : "text-neutral-500"
                                        )} />
                                        <div>
                                            <p className="font-medium text-neutral-200 text-sm">{type.label}</p>
                                            <p className="text-xs text-neutral-500 mt-1">{type.description}</p>
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {selectedType && (
                        <div className="mt-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-start gap-2">
                            <Info className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                            <p className="text-xs text-blue-300">
                                الحقول المطلوبة في القالب: <code className="bg-black/30 px-1 rounded">{selectedType.requiredFields.join(', ')}</code>
                            </p>
                        </div>
                    )}
                </div>

                {/* Prompts */}
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6">
                    <h3 className="text-lg font-bold text-neutral-200 mb-4">الأوامر (Prompts)</h3>

                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium text-neutral-400 block mb-2">System Prompt *</label>
                            <textarea
                                value={formData.system_prompt}
                                onChange={(e) => handleChange('system_prompt', e.target.value)}
                                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none min-h-[120px] font-mono text-sm"
                                placeholder="You are a helpful AI assistant..."
                                required
                                dir="ltr"
                            />
                            <p className="text-xs text-neutral-500 mt-1">يحدد شخصية وسلوك الوكيل</p>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-neutral-400 block mb-2">User Prompt Template *</label>
                            <textarea
                                value={formData.user_prompt}
                                onChange={(e) => handleChange('user_prompt', e.target.value)}
                                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none min-h-[150px] font-mono text-sm"
                                placeholder="Task: {task}&#10;Context: {context}"
                                required
                                dir="ltr"
                            />
                            <p className="text-xs text-neutral-500 mt-1">
                                استخدم {'{field}'} للحقول الديناميكية. الحقول المطلوبة: {selectedType?.requiredFields.map(f => `{${f}}`).join(', ')}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Status */}
                <div className="rounded-2xl border border-white/5 bg-surface/30 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="font-medium text-neutral-200">تفعيل الوكيل</h3>
                            <p className="text-xs text-neutral-500 mt-1">الوكيل سيكون جاهزاً للاستخدام فور الإنشاء</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={formData.is_active}
                                onChange={(e) => handleChange('is_active', e.target.checked)}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                        </label>
                    </div>
                </div>

                {/* Error */}
                {error && (
                    <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {/* Submit */}
                <div className="flex justify-end gap-3">
                    <Link
                        to="/agents"
                        className="px-6 py-3 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors font-medium"
                    >
                        إلغاء
                    </Link>
                    <button
                        type="submit"
                        disabled={saving || !formData.name || !formData.system_prompt || !formData.user_prompt}
                        className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                    >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        إنشاء الوكيل
                    </button>
                </div>
            </form>
        </DashboardLayout>
    );
}
