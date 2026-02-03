import React, { useEffect, useState } from 'react';
import { Play, Pause, RefreshCw, Settings as SettingsIcon, Terminal, Plus, Trash2, TestTube, Edit, ChevronDown, ChevronUp, Loader2, Bot, Zap, Search, FileText, Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const AGENT_TYPE_ICONS = {
    router: Zap,
    monitor: Cpu,
    editor: FileText,
    search: Search,
    general: Bot,
    custom: SettingsIcon,
};

const AGENT_TYPE_LABELS = {
    router: 'موجّه',
    monitor: 'مراقب',
    editor: 'محرر',
    search: 'باحث',
    general: 'عام',
    custom: 'مخصص',
};

const AgentRow = ({ agent, onToggle, onDelete, onTest, expanded, onExpand, loading, testing }) => {
    const TypeIcon = AGENT_TYPE_ICONS[agent.agent_type] || Bot;

    return (
        <div className="border-b border-white/5 last:border-b-0">
            {/* Main Row */}
            <div className="flex items-center gap-4 p-4 hover:bg-white/5 transition-colors">
                {/* Status Indicator */}
                <div className={cn(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    agent.is_active ? "bg-emerald-500" : "bg-neutral-600"
                )} />

                {/* Icon */}
                <div className={cn(
                    "p-2 rounded-lg flex-shrink-0",
                    agent.is_active ? "bg-primary/10 text-primary" : "bg-white/5 text-neutral-500"
                )}>
                    <TypeIcon className="h-4 w-4" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <h3 className="font-medium text-neutral-100 truncate">{agent.name}</h3>
                        <span className="text-xs px-2 py-0.5 rounded bg-white/5 text-neutral-500 border border-white/5">
                            {AGENT_TYPE_LABELS[agent.agent_type] || agent.agent_type}
                        </span>
                        {agent.is_system && (
                            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                نظام
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-neutral-500 truncate mt-0.5">
                        {agent.description || 'بدون وصف'}
                    </p>
                </div>

                {/* Key */}
                <div className="hidden md:block">
                    <code className="text-xs px-2 py-1 rounded bg-black/30 text-neutral-400 font-mono">
                        {agent.key}
                    </code>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => onTest(agent)}
                        disabled={testing === agent.id}
                        className="p-2 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                        title="اختبار"
                    >
                        {testing === agent.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <TestTube className="h-4 w-4" />
                        )}
                    </button>
                    <button
                        onClick={() => onToggle(agent)}
                        disabled={loading === agent.id}
                        className={cn(
                            "p-2 rounded-lg transition-colors",
                            agent.is_active
                                ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                                : "bg-white/5 text-neutral-400 hover:bg-white/10"
                        )}
                        title={agent.is_active ? "إيقاف" : "تشغيل"}
                    >
                        {loading === agent.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : agent.is_active ? (
                            <Pause className="h-4 w-4" />
                        ) : (
                            <Play className="h-4 w-4" />
                        )}
                    </button>
                    <Link
                        to={`/agents/${agent.id}/edit`}
                        className="p-2 rounded-lg bg-white/5 text-neutral-400 hover:bg-white/10 transition-colors"
                        title="تعديل"
                    >
                        <Edit className="h-4 w-4" />
                    </Link>
                    {!agent.is_system && (
                        <button
                            onClick={() => onDelete(agent.id)}
                            className="p-2 rounded-lg bg-white/5 text-neutral-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                            title="حذف"
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    )}
                    <button
                        onClick={() => onExpand(expanded === agent.id ? null : agent.id)}
                        className="p-2 rounded-lg bg-white/5 text-neutral-400 hover:bg-white/10 transition-colors"
                        title="تفاصيل"
                    >
                        {expanded === agent.id ? (
                            <ChevronUp className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </button>
                </div>
            </div>

            {/* Expanded Details */}
            {expanded === agent.id && (
                <div className="px-4 pb-4 bg-black/20 border-t border-white/5">
                    <div className="grid md:grid-cols-2 gap-4 pt-4">
                        <div>
                            <label className="text-xs text-neutral-500 block mb-1">System Prompt</label>
                            <pre className="text-xs text-neutral-300 bg-black/30 p-3 rounded-lg overflow-x-auto max-h-32 whitespace-pre-wrap">
                                {agent.system_prompt}
                            </pre>
                        </div>
                        <div>
                            <label className="text-xs text-neutral-500 block mb-1">User Prompt Template</label>
                            <pre className="text-xs text-neutral-300 bg-black/30 p-3 rounded-lg overflow-x-auto max-h-32 whitespace-pre-wrap">
                                {agent.user_prompt}
                            </pre>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default function Agents() {
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);
    const [testing, setTesting] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [testResult, setTestResult] = useState(null);
    const [testTask, setTestTask] = useState('');
    const [showTestModal, setShowTestModal] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState(null);

    const fetchAgents = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/agents');
            if (res.ok) {
                const data = await res.json();
                setAgents(data);
            }
        } catch (err) {
            console.error("Failed to fetch agents", err);
        } finally {
            setLoading(false);
        }
    };

    const toggleAgent = async (agent) => {
        setActionLoading(agent.id);
        try {
            const res = await fetch(`/api/agents/${agent.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !agent.is_active })
            });
            if (res.ok) {
                const updated = await res.json();
                setAgents(agents.map(a => a.id === agent.id ? updated : a));
            }
        } catch (err) {
            console.error("Failed to toggle agent", err);
        } finally {
            setActionLoading(null);
        }
    };

    const deleteAgent = async (id) => {
        if (!confirm("هل أنت متأكد من حذف هذا الوكيل؟")) return;
        setActionLoading(id);
        try {
            const res = await fetch(`/api/agents/${id}`, { method: 'DELETE' });
            if (res.ok || res.status === 204) {
                setAgents(agents.filter(a => a.id !== id));
            }
        } catch (err) {
            console.error("Failed to delete agent", err);
        } finally {
            setActionLoading(null);
        }
    };

    const openTestModal = (agent) => {
        setSelectedAgent(agent);
        setTestTask('');
        setTestResult(null);
        setShowTestModal(true);
    };

    const runTest = async () => {
        if (!selectedAgent || !testTask.trim()) return;

        setTesting(selectedAgent.id);
        setTestResult(null);

        try {
            const res = await fetch('/api/agents/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task: testTask,
                    route: selectedAgent.key,
                    // If system agent, send specific fields
                    ...(selectedAgent.is_system ? { agent_type: selectedAgent.agent_type } : {})
                })
            });

            let data;
            const contentType = res.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                data = await res.json();
            } else {
                const text = await res.text();
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    data = { error: text || res.statusText };
                }
            }

            setTestResult({
                success: res.ok,
                data: data
            });
        } catch (err) {
            console.error("Agent run error:", err);
            setTestResult({
                success: false,
                data: { error: err.message || "فشل الاتصال بالخادم" }
            });
        } finally {
            setTesting(null);
        }
    };

    useEffect(() => {
        fetchAgents();
    }, []);

    // Group agents
    const systemAgents = agents.filter(a => a.is_system);
    const customAgents = agents.filter(a => !a.is_system);

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                        الوكلاء الأذكياء
                    </h2>
                    <p className="text-sm text-neutral-500">إدارة ومراقبة وكلاء الذكاء الاصطناعي</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={fetchAgents}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors text-sm font-medium border border-white/10"
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                        تحديث
                    </button>
                    <Link
                        to="/agents/add"
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors text-sm font-bold shadow-lg shadow-primary/20"
                    >
                        <Plus className="h-4 w-4" />
                        إنشاء وكيل
                    </Link>
                </div>
            </div>

            {/* Loading */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <div className="space-y-6">
                    {/* System Agents */}
                    {systemAgents.length > 0 && (
                        <div className="rounded-2xl border border-white/5 bg-surface/30 overflow-hidden">
                            <div className="px-4 py-3 bg-surface/50 border-b border-white/5">
                                <h3 className="text-sm font-bold text-neutral-300">وكلاء النظام</h3>
                            </div>
                            {systemAgents.map(agent => (
                                <AgentRow
                                    key={agent.id}
                                    agent={agent}
                                    onToggle={toggleAgent}
                                    onDelete={deleteAgent}
                                    onTest={openTestModal}
                                    expanded={expanded}
                                    onExpand={setExpanded}
                                    loading={actionLoading}
                                    testing={testing}
                                />
                            ))}
                        </div>
                    )}

                    {/* Custom Agents */}
                    <div className="rounded-2xl border border-white/5 bg-surface/30 overflow-hidden">
                        <div className="px-4 py-3 bg-surface/50 border-b border-white/5">
                            <h3 className="text-sm font-bold text-neutral-300">وكلاء مخصصين</h3>
                        </div>
                        {customAgents.length > 0 ? (
                            customAgents.map(agent => (
                                <AgentRow
                                    key={agent.id}
                                    agent={agent}
                                    onToggle={toggleAgent}
                                    onDelete={deleteAgent}
                                    onTest={openTestModal}
                                    expanded={expanded}
                                    onExpand={setExpanded}
                                    loading={actionLoading}
                                    testing={testing}
                                />
                            ))
                        ) : (
                            <div className="py-12 text-center text-neutral-500">
                                <Bot className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                <p>لا يوجد وكلاء مخصصين</p>
                                <Link to="/agents/add" className="text-primary text-sm mt-2 inline-block hover:underline">
                                    إنشاء وكيل جديد
                                </Link>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Test Modal */}
            {showTestModal && selectedAgent && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#141416] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
                        <div className="p-4 border-b border-white/5 flex items-center justify-between">
                            <h3 className="font-bold text-neutral-100">اختبار الوكيل: {selectedAgent.name}</h3>
                            <button
                                onClick={() => setShowTestModal(false)}
                                className="text-neutral-500 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div>
                                <label className="text-sm text-neutral-400 block mb-2">المهمة (Task)</label>
                                <textarea
                                    value={testTask}
                                    onChange={(e) => setTestTask(e.target.value)}
                                    className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-neutral-200 placeholder:text-neutral-600 focus:border-primary/50 focus:outline-none min-h-[100px] text-sm"
                                    placeholder="أدخل المهمة التي تريد تنفيذها..."
                                />
                            </div>
                            <button
                                onClick={runTest}
                                disabled={testing || !testTask.trim()}
                                className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                            >
                                {testing ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        جاري التنفيذ...
                                    </>
                                ) : (
                                    <>
                                        <TestTube className="h-4 w-4" />
                                        تشغيل الاختبار
                                    </>
                                )}
                            </button>

                            {testResult && (
                                <div className={cn(
                                    "p-4 rounded-xl border",
                                    testResult.success
                                        ? "bg-emerald-500/10 border-emerald-500/20"
                                        : "bg-red-500/10 border-red-500/20"
                                )}>
                                    <label className="text-xs text-neutral-500 block mb-2">النتيجة:</label>
                                    <pre className="text-sm text-neutral-300 whitespace-pre-wrap overflow-x-auto max-h-64">
                                        {typeof testResult.data?.output === 'string'
                                            ? testResult.data.output
                                            : JSON.stringify(testResult.data, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </DashboardLayout>
    );
}
