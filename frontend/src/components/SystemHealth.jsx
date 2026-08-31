import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, Layers, Cpu, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { fetchSystemHealth } from '../api/client';

export default function SystemHealth({ onStatusUpdate }) {
  const [healthData, setHealthData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadHealth = async () => {
    setIsLoading(true);
    const data = await fetchSystemHealth();
    setHealthData(data);
    setIsLoading(false);
    if (onStatusUpdate) onStatusUpdate(data.status);
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="flex-1 p-6 bg-slate-950 overflow-y-auto space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <Activity className="w-5 h-5 text-emerald-400" />
              <span>System Operations & Infrastructure Health</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Live status monitoring of ThreatLens microservices, database connections, and model pipelines.
            </p>
          </div>

          <button
            onClick={loadHealth}
            disabled={isLoading}
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition-all flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {healthData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Overall Status */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center space-x-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${healthData.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall API Status</h3>
                  <div className="text-sm font-bold text-white capitalize">{healthData.status}</div>
                </div>
              </div>
              <div className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                Version: <code className="text-blue-400">1.0.0</code> | Last checked: {new Date(healthData.timestamp).toLocaleTimeString()}
              </div>
            </div>

            {/* Postgres */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Metadata Storage</h3>
                  <div className="text-sm font-bold text-white flex items-center space-x-1.5">
                    <span>PostgreSQL / SQLite</span>
                    {healthData.services?.postgres?.status === 'healthy' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 inline ml-1" />
                    ) : (
                      <span className="text-[10px] text-amber-400 font-mono">(Fallback Active)</span>
                    )}
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                {healthData.services?.postgres?.description || 'SQL Metadata database'}
              </p>
            </div>

            {/* Qdrant */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Vector Store</h3>
                  <div className="text-sm font-bold text-white flex items-center space-x-1.5">
                    <span>Qdrant Vector Database</span>
                    {healthData.services?.qdrant?.status === 'healthy' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 inline ml-1" />
                    ) : (
                      <span className="text-[10px] text-amber-400 font-mono">(Embedded Active)</span>
                    )}
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                {healthData.services?.qdrant?.description || 'Qdrant vector database'}
              </p>
            </div>

            {/* LLM Engine */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">LLM Inference Provider</h3>
                  <div className="text-sm font-bold text-white">OpenAI / Ollama Local</div>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                Generative AI Guardrails & Groundedness Filter Enabled
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
