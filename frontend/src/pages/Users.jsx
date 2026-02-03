import React, { useEffect, useState } from 'react';
import { Users as UsersIcon, UserPlus, RefreshCw, Trash2, KeyRound, ShieldCheck, Download, DatabaseBackup, ToggleLeft, ToggleRight, Search } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import { cn } from '../lib/utils';

const STAT_ITEMS = [
  { key: 'total_users', label: 'إجمالي المستخدمين', color: 'emerald' },
  { key: 'active_users', label: 'المستخدمون النشطون', color: 'cyan' },
  { key: 'total_sessions', label: 'إجمالي المحادثات', color: 'amber' },
  { key: 'total_messages', label: 'إجمالي الرسائل', color: 'purple' },
];

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleString('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function Users() {
  const [stats, setStats] = useState({
    total_users: 0,
    active_users: 0,
    total_sessions: 0,
    total_messages: 0,
  });
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [savingId, setSavingId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({ display_name: '', username: '', password: '' });
  const [resetTarget, setResetTarget] = useState(null);
  const [resetPassword, setResetPassword] = useState('');
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const visibleUsers = users;

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/users/stats');
      if (res.ok) {
        setStats(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch user stats', err);
    }
  };

  const fetchUsers = async (nextPage = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(pageSize));
      params.set('offset', String((nextPage - 1) * pageSize));
      if (search.trim()) {
        params.set('search', search.trim());
      }
      if (statusFilter !== 'all') {
        params.set('is_active', statusFilter === 'active' ? 'true' : 'false');
      }
      const res = await fetch(`/api/users?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data.items || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error('Failed to fetch users', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchRegistration();
  }, []);

  useEffect(() => {
    setPage(1);
    fetchUsers(1);
  }, [search, statusFilter]);

  const fetchRegistration = async () => {
    try {
      const res = await fetch('/api/users/registration');
      if (res.ok) {
        const data = await res.json();
        setRegistrationEnabled(Boolean(data.enabled));
      }
    } catch (err) {
      console.error('Failed to fetch registration status', err);
    }
  };

  const handleCreate = async () => {
    if (!createForm.username.trim() || !createForm.display_name.trim() || createForm.password.length < 6) {
      return;
    }
    setCreating(true);
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: createForm.username.trim(),
          display_name: createForm.display_name.trim(),
          password: createForm.password,
        }),
      });
      if (res.ok) {
        setCreateForm({ display_name: '', username: '', password: '' });
        setShowCreateModal(false);
        await fetchUsers(1);
        await fetchStats();
      }
    } catch (err) {
      console.error('Failed to create user', err);
    } finally {
      setCreating(false);
    }
  };

  const handleRegistrationToggle = async () => {
    const nextValue = !registrationEnabled;
    try {
      const res = await fetch('/api/users/registration', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextValue }),
      });
      if (res.ok) {
        setRegistrationEnabled(nextValue);
      }
    } catch (err) {
      console.error('Failed to toggle registration', err);
    }
  };

  const downloadFile = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleExport = async () => {
    try {
      const res = await fetch('/api/users/export');
      if (!res.ok) return;
      const blob = await res.blob();
      const filename = res.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'users_export.csv';
      downloadFile(blob, filename);
    } catch (err) {
      console.error('Failed to export users', err);
    }
  };

  const handleBackup = async () => {
    try {
      const res = await fetch('/api/users/backup');
      if (!res.ok) return;
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const filename = `users_backup_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '')}.json`;
      downloadFile(blob, filename);
    } catch (err) {
      console.error('Failed to backup users', err);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pageStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = Math.min(total, page * pageSize);

  const handleToggleActive = async (user) => {
    setSavingId(user.id);
    try {
      const res = await fetch(`/api/users/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUsers((prev) => prev.map((item) => (item.id === user.id ? { ...item, ...updated } : item)));
        await fetchStats();
      }
    } catch (err) {
      console.error('Failed to update user', err);
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (user) => {
    const confirmed = window.confirm(`حذف المستخدم ${user.username}؟`);
    if (!confirmed) return;
    setSavingId(user.id);
    try {
      const res = await fetch(`/api/users/${user.id}`, { method: 'DELETE' });
      if (res.ok) {
        setUsers((prev) => prev.filter((item) => item.id !== user.id));
        await fetchStats();
      }
    } catch (err) {
      console.error('Failed to delete user', err);
    } finally {
      setSavingId(null);
    }
  };

  const handleResetPassword = async () => {
    if (!resetTarget || resetPassword.length < 6) {
      return;
    }
    setSavingId(resetTarget.id);
    try {
      const res = await fetch(`/api/users/${resetTarget.id}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: resetPassword }),
      });
      if (res.ok) {
        setResetTarget(null);
        setResetPassword('');
      }
    } catch (err) {
      console.error('Failed to reset password', err);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            المستخدمون
          </h2>
          <p className="text-sm text-neutral-500">إدارة الحسابات، المحادثات، وإعادة تعيين كلمات المرور</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRegistrationToggle}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium border",
              registrationEnabled
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                : "border-red-500/30 bg-red-500/10 text-red-200"
            )}
          >
            {registrationEnabled ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
            {registrationEnabled ? 'التسجيل مفتوح' : 'التسجيل مغلق'}
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium border border-white/10 text-neutral-300 hover:bg-white/5"
          >
            <Download className="h-4 w-4" />
            تصدير
          </button>
          <button
            onClick={handleBackup}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium border border-white/10 text-neutral-300 hover:bg-white/5"
          >
            <DatabaseBackup className="h-4 w-4" />
            نسخة احتياطية
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/90 text-emerald-950 font-medium hover:bg-emerald-400 transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            إنشاء مستخدم
          </button>
          <button
            onClick={() => {
              fetchStats();
              fetchUsers();
            }}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 text-neutral-300 rounded-xl hover:bg-white/10 transition-colors text-sm font-medium border border-white/10"
          >
            <RefreshCw className="h-4 w-4" />
            تحديث
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {STAT_ITEMS.map((item) => (
          <div
            key={item.key}
            className={cn(
              "rounded-xl p-4 border",
              `border-${item.color}-500/20 bg-${item.color}-500/10`
            )}
          >
            <div className="flex items-center gap-3">
              <div className={cn("p-2 rounded-lg", `bg-${item.color}-500/20 text-${item.color}-400`)}>
                <UsersIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-neutral-100">{stats[item.key] || 0}</p>
                <p className="text-xs text-neutral-500">{item.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-white/5 bg-surface/40 p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="h-4 w-4 text-neutral-500 absolute right-3 top-1/2 -translate-y-1/2" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="بحث باسم المستخدم أو البريد الإلكتروني..."
              className="w-full bg-transparent border border-white/10 rounded-xl pr-10 pl-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-400/60"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-transparent border border-white/10 rounded-xl px-3 py-2 text-sm text-neutral-200 focus:outline-none"
          >
            <option value="all">كل المستخدمين</option>
            <option value="active">النشطون فقط</option>
            <option value="inactive">الموقوفون فقط</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-right">
            <thead>
              <tr className="text-xs text-neutral-400 border-b border-white/5">
                <th className="py-3 px-2">الاسم</th>
                <th className="py-3 px-2">البريد</th>
                <th className="py-3 px-2">الحالة</th>
                <th className="py-3 px-2">المحادثات</th>
                <th className="py-3 px-2">الرسائل</th>
                <th className="py-3 px-2">آخر دخول</th>
                <th className="py-3 px-2">آخر محادثة</th>
                <th className="py-3 px-2">تاريخ الإنشاء</th>
                <th className="py-3 px-2">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-neutral-500">جاري التحميل...</td>
                </tr>
              ) : visibleUsers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-neutral-500">لا يوجد مستخدمون</td>
                </tr>
              ) : (
                visibleUsers.map((user) => (
                  <tr key={user.id} className="border-b border-white/5">
                    <td className="py-3 px-2 text-neutral-100 font-medium">{user.display_name || user.username}</td>
                    <td className="py-3 px-2 text-neutral-400">{user.username}</td>
                    <td className="py-3 px-2">
                      <span
                        className={cn(
                          "text-xs px-2 py-1 rounded-full",
                          user.is_active
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-red-500/15 text-red-400"
                        )}
                      >
                        {user.is_active ? 'نشط' : 'موقوف'}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-neutral-300">{user.session_count}</td>
                    <td className="py-3 px-2 text-neutral-300">{user.message_count}</td>
                    <td className="py-3 px-2 text-neutral-500">{formatDate(user.last_login_at)}</td>
                    <td className="py-3 px-2 text-neutral-500">{formatDate(user.last_session_at)}</td>
                    <td className="py-3 px-2 text-neutral-500">{formatDate(user.created_at)}</td>
                    <td className="py-3 px-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={savingId === user.id}
                          className={cn(
                            "px-3 py-1 rounded-lg text-xs border",
                            user.is_active
                              ? "border-red-500/30 text-red-300 hover:bg-red-500/10"
                              : "border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10"
                          )}
                        >
                          {user.is_active ? 'إيقاف' : 'تفعيل'}
                        </button>
                        <button
                          onClick={() => setResetTarget(user)}
                          className="px-3 py-1 rounded-lg text-xs border border-white/10 text-neutral-300 hover:bg-white/5"
                        >
                          إعادة تعيين
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          className="px-3 py-1 rounded-lg text-xs border border-red-500/30 text-red-300 hover:bg-red-500/10"
                        >
                          حذف
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-4 text-sm text-neutral-500">
          <div>عرض {pageStart} - {pageEnd} من {total}</div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                const next = Math.max(1, page - 1);
                setPage(next);
                fetchUsers(next);
              }}
              disabled={page === 1}
              className="px-3 py-1 rounded-lg border border-white/10 disabled:opacity-50"
            >
              السابق
            </button>
            <button
              onClick={() => {
                const next = Math.min(totalPages, page + 1);
                setPage(next);
                fetchUsers(next);
              }}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded-lg border border-white/10 disabled:opacity-50"
            >
              التالي
            </button>
          </div>
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-surface p-6">
            <h3 className="text-lg font-semibold text-neutral-100 mb-2">إنشاء مستخدم جديد</h3>
            <p className="text-xs text-neutral-500 mb-4">كل المستخدمين بصلاحية عادية</p>
            <div className="space-y-3">
            <input
              value={createForm.display_name}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, display_name: e.target.value }))}
              placeholder="الاسم الكامل"
              className="w-full bg-transparent border border-white/10 rounded-xl px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-400/60"
            />
            <input
              value={createForm.username}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, username: e.target.value }))}
              placeholder="البريد الإلكتروني"
              className="w-full bg-transparent border border-white/10 rounded-xl px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-400/60"
            />
              <input
                value={createForm.password}
                onChange={(e) => setCreateForm((prev) => ({ ...prev, password: e.target.value }))}
                placeholder="كلمة المرور (6 أحرف على الأقل)"
                type="password"
                className="w-full bg-transparent border border-white/10 rounded-xl px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-400/60"
              />
            </div>
            <div className="flex gap-2 mt-5">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 px-4 py-2 rounded-xl bg-emerald-500/90 text-emerald-950 font-medium"
              >
                إنشاء
              </button>
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 rounded-xl border border-white/10 text-neutral-300"
              >
                إلغاء
              </button>
            </div>
          </div>
        </div>
      )}

      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-surface p-6">
            <h3 className="text-lg font-semibold text-neutral-100 mb-2">إعادة تعيين كلمة المرور</h3>
            <p className="text-xs text-neutral-500 mb-4">المستخدم: {resetTarget.username}</p>
            <input
              value={resetPassword}
              onChange={(e) => setResetPassword(e.target.value)}
              placeholder="كلمة المرور الجديدة"
              type="password"
              className="w-full bg-transparent border border-white/10 rounded-xl px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-400/60"
            />
            <div className="flex gap-2 mt-5">
              <button
                onClick={handleResetPassword}
                className="flex-1 px-4 py-2 rounded-xl bg-emerald-500/90 text-emerald-950 font-medium"
              >
                حفظ
              </button>
              <button
                onClick={() => {
                  setResetTarget(null);
                  setResetPassword('');
                }}
                className="flex-1 px-4 py-2 rounded-xl border border-white/10 text-neutral-300"
              >
                إلغاء
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
