import React from 'react';
import { MessageSquare, AlertTriangle, Search, BookOpen, Database, Activity } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const menuItems = [
    { id: 'chat', label: 'AI RAG Copilot', icon: MessageSquare, badge: 'RAG' },
    { id: 'alert', label: 'Alert Explainer', icon: AlertTriangle },
    { id: 'cve', label: 'CVE Vulnerability Search', icon: Search },
    { id: 'playbooks', label: 'SOC Playbooks', icon: BookOpen },
    { id: 'ingestion', label: 'Ingestion Manager', icon: Database },
    { id: 'health', label: 'System Health', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-slate-900/50 border-r border-slate-800 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-6">
        <div>
          <h2 className="px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            SOC Operations Hub
          </h2>
          <nav className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm shadow-blue-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] font-bold bg-blue-500/20 text-blue-300 rounded-md">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
        <div className="font-semibold text-slate-300 flex items-center justify-between">
          <span>RAG Pipeline</span>
          <span className="text-[10px] text-emerald-400 font-mono">ACTIVE</span>
        </div>
        <p className="text-[10px] text-slate-500">Hybrid Dense Vector + Sparse BM25 Search</p>
      </div>
    </aside>
  );
}
