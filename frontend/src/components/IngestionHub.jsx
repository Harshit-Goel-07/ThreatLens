import React, { useState, useEffect } from 'react';
import { Database, Play, RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { apiFetch } from '../api/client';

export default function IngestionHub() {
  const [sources, setSources] = useState([
    { name: 'mitre', description: 'MITRE ATT&CK techniques and tactics', enabled: true },
    { name: 'cve', description: 'CVE vulnerability database (NVD)', enabled: true },
    { name: 'logs', description: 'Security logs (Sysmon, Windows Event, auditd)', enabled: true },
    { name: 'playbooks', description: 'SOC incident response playbooks', enabled: true },
  ]);
  const [activeJobs, setActiveJobs] = useState({});
  const [loadingSource, setLoadingSource] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const triggerIngestion = async (sourceName) => {
    setLoadingSource(sourceName);
    setErrorMsg('');
    try {
      const data = await apiFetch('/api/v1/ingest', {
        method: 'POST',
        body: JSON.stringify({
          source_type: sourceName,
          batch_size: 100,
        }),
      });

      if (data.job_id) {
        setActiveJobs((prev) => ({
          ...prev,
          [sourceName]: { job_id: data.job_id, status: 'queued', progress: 0 },
        }));
        pollJobStatus(data.job_id, sourceName);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Ingestion failed to trigger. Admin access may be required.');
    } finally {
      setLoadingSource(null);
    }
  };

  const pollJobStatus = async (jobId, sourceName) => {
    const interval = setInterval(async () => {
      try {
        const statusData = await apiFetch(`/api/v1/ingest/${jobId}`);
        setActiveJobs((prev) => ({
          ...prev,
          [sourceName]: statusData,
        }));
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  };

  return (
    <div className="flex-1 p-6 bg-slate-950 overflow-y-auto space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Database className="w-5 h-5 text-blue-400" />
            <span>Ingestion & Knowledge Management Hub</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Trigger data ingestion pipelines to chunk, embed, and index security knowledge into Qdrant vector store.
          </p>
        </div>

        {errorMsg && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
            {errorMsg}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map((src) => {
            const job = activeJobs[src.name];
            const isIngesting = loadingSource === src.name || (job && (job.status === 'pending' || job.status === 'running'));

            return (
              <div key={src.name} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white capitalize">{src.name} Source</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{src.description}</p>
                  </div>
                  <button
                    onClick={() => triggerIngestion(src.name)}
                    disabled={isIngesting}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold rounded-xl text-xs transition-all flex items-center space-x-1.5 shadow-md shadow-blue-600/10"
                  >
                    {isIngesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                    <span>Ingest</span>
                  </button>
                </div>

                {/* Job Status Banner */}
                {job && (
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-slate-300">Status: <span className="uppercase text-blue-400">{job.status}</span></span>
                      <span>Job: {job.job_id}</span>
                    </div>

                    {job.progress !== undefined && (
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-blue-500 h-full transition-all duration-300"
                          style={{ width: `${Math.min(100, Math.max(5, (job.progress || 0) * 100))}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
