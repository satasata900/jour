import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Radio, Settings, Users, Database, FileText } from 'lucide-react';
import { cn } from '../lib/utils';

export default function DashboardLayout({ children }) {
    const navItems = [
        { to: '/', icon: LayoutDashboard, label: 'لوحة المعلومات', end: true },
        { to: '/feed', icon: Radio, label: 'البث المباشر' },
        { to: '/agents', icon: Users, label: 'الوكلاء الأذكياء' },
        { to: '/sources', icon: Database, label: 'المصادر' },
        { to: '/summaries', icon: FileText, label: 'الملخصات' },
        { to: '/users', icon: Users, label: 'المستخدمون' },
        { to: '/settings', icon: Settings, label: 'الإعدادات' },
    ];

    return (
        <div className="flex min-h-screen bg-background text-foreground font-sans">
            {/* Sidebar */}
            <aside className="fixed inset-y-0 right-0 z-50 w-64 border-l border-border bg-surface/50 backdrop-blur-xl lg:static lg:inset-auto">
                <div className="flex h-16 items-center justify-center border-b border-border px-6">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                        المساعد الصحفي
                    </h1>
                </div>

                <nav className="space-y-1 p-4">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            className={({ isActive }) =>
                                cn(
                                    'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
                                    isActive
                                        ? 'bg-primary/10 text-primary shadow-sm shadow-primary/20'
                                        : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                                )
                            }
                        >
                            <item.icon className="h-5 w-5" />
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="absolute bottom-4 left-0 right-0 px-4">
                    <div className="rounded-xl bg-gradient-to-br from-emerald-900/20 to-cyan-900/20 p-4 border border-white/5">
                        <p className="text-xs text-emerald-400 font-medium mb-1">الحالة: متصل</p>
                        <p className="text-[10px] text-neutral-500">v2.0.0 (Beta)</p>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-x-hidden">
                <div className="container mx-auto p-4 lg:p-8 max-w-7xl">
                    {children}
                </div>
            </main>
        </div>
    );
}
