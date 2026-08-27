import React, { useState } from 'react';
import { Search, ShieldAlert, CheckCircle, ExternalLink, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';

export default function CveLookup() {
  const [cveQuery, setCveQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleLookup = async () => {
    if (!cveQuery.trim()) return;
    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const data = await apiFetch('/api/v1/cve/lookup', {
        method: 'POST',
        body: JSON.stringify({
          query: cveQuery.trim(),
          top_k: 5,
        }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message || 'CVE Lookup failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 bg-slate-950 overflow-y-auto space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            <span>CVE Vulnerability Lookup</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Search NVD CVE records by ID (e.g. CVE-2021-44228) or product keywords to inspect CVSS scores, affected software, and mitigations.
          </p>
        </div>

        <div className="flex space-x-3">
          <input
            type="text"
            value={cveQuery}
            onChange={(e) => setCveQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
            placeholder="Enter CVE ID or keyword (e.g. CVE-2023-34362 or Log4j)..."
            className="flex-1 px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500"
          />
          <button
            onClick={handleLookup}
            disabled={isLoading || !cveQuery.trim()}
            className="px-6 py-3 bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 text-white font-semibold rounded-xl text-xs transition-all shadow-md shadow-rose-600/20 flex items-center space-x-2"
          >
            {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search CVE</span>
          </button>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-sm font-bold text-white">CVE Intelligence Summary</h3>
              <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold rounded-lg">
                NVD Verified
              </span>
            </div>

            <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </div>

            {result.sources && result.sources.length > 0 && (
              <div className="pt-4 border-t border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold text-slate-400">Associated CVE References</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-1">
                      <div className="font-bold text-rose-300">{src.doc_id || src.title}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-3">{src.snippet}</div>
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
