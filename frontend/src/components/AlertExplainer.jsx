import React, { useState } from 'react';
import { AlertTriangle, Sparkles, Shield, ArrowRight, CheckCircle, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import FormattedResponse from './FormattedResponse';

export default function AlertExplainer() {
  const [alertText, setAlertText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleExplain = async () => {
    if (!alertText.trim()) return;
    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const data = await apiFetch('/api/v1/alert/explain', {
        method: 'POST',
        body: JSON.stringify({
          query: alertText.trim(),
          top_k: 5,
        }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Alert analysis failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 bg-slate-950 overflow-y-auto space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <span>SOC Alert Explainer & Triage</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Paste raw SIEM alert logs, EDR notifications, or event details to receive instant AI triage and response steps.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <textarea
            rows={6}
            value={alertText}
            onChange={(e) => setAlertText(e.target.value)}
            placeholder="Paste alert payload or log snippet here (e.g. Sysmon Event ID 1: powershell.exe -enc ...)"
            className="w-full p-3.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500 font-mono"
          />

          <div className="flex justify-between items-center">
            <div className="text-[11px] text-slate-500">Supported formats: JSON, Sysmon, Windows Event Log, Auditd</div>
            <button
              onClick={handleExplain}
              disabled={isLoading || !alertText.trim()}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold rounded-xl text-xs transition-all flex items-center space-x-2 shadow-md shadow-amber-500/10"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Analyzing Alert...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Explain Alert</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Triage & Analysis Report</h3>
                  <p className="text-[11px] text-slate-400">ThreatLens AI Evaluation</p>
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-300 leading-relaxed">
              <FormattedResponse content={result.answer} />
            </div>

            {result.sources && result.sources.length > 0 && (
              <div className="pt-4 border-t border-slate-800">
                <h4 className="text-xs font-semibold text-slate-400 mb-3">Matching Threat Intelligence</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-1">
                      <div className="font-bold text-slate-200">{src.title || src.doc_id}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-2">{src.snippet}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
