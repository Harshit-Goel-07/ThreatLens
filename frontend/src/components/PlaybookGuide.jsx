import React, { useState } from 'react';
import { BookOpen, CheckSquare, ShieldCheck, ArrowRight, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import FormattedResponse from './FormattedResponse';

const PLAYBOOK_TOPICS = [
  { id: 'phishing', label: 'Phishing & Email Compromise', severity: 'HIGH' },
  { id: 'ransomware', label: 'Ransomware Outbreak & Containment', severity: 'CRITICAL' },
  { id: 'malware', label: 'Endpoint Malware Execution', severity: 'MEDIUM' },
  { id: 'unauthorized_access', label: 'Privilege Escalation & Lateral Movement', severity: 'HIGH' },
];

export default function PlaybookGuide() {
  const [selectedTopic, setSelectedTopic] = useState(PLAYBOOK_TOPICS[0].id);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);

  const fetchGuidance = async (topicId) => {
    setSelectedTopic(topicId);
    setIsLoading(true);
    setResult(null);

    const topicObj = PLAYBOOK_TOPICS.find((t) => t.id === topicId);
    try {
      const data = await apiFetch('/api/v1/incident/guidance', {
        method: 'POST',
        body: JSON.stringify({
          query: `Provide incident response guidance for ${topicObj.label}`,
          top_k: 5,
        }),
      });
      setResult(data);
    } catch (err) {
      console.error('Playbook error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 bg-slate-950 overflow-y-auto space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-indigo-400" />
            <span>SOC Incident Response Playbooks</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Access standardized, battle-tested incident response procedures, checklists, and escalation guidelines.
          </p>
        </div>

        {/* Topic Selector */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PLAYBOOK_TOPICS.map((topic) => (
            <button
              key={topic.id}
              onClick={() => fetchGuidance(topic.id)}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedTopic === topic.id
                  ? 'bg-indigo-600/10 border-indigo-500/40 text-white shadow-lg shadow-indigo-500/10'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-xs">{topic.label}</span>
                <span
                  className={`text-[9px] px-2 py-0.5 rounded font-bold ${
                    topic.severity === 'CRITICAL'
                      ? 'bg-rose-500/20 text-rose-300'
                      : topic.severity === 'HIGH'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-blue-500/20 text-blue-300'
                  }`}
                >
                  {topic.severity}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 flex items-center space-x-1">
                <span>View Standard Operating Procedure</span>
                <ArrowRight className="w-3 h-3 ml-1" />
              </div>
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-2xl">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-400 mb-2" />
            <p className="text-xs">Loading SOC Playbook procedures...</p>
          </div>
        ) : result ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div className="flex items-center space-x-3 border-b border-slate-800 pb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Execution Playbook Guide</h3>
                <p className="text-[11px] text-slate-400">SOC Triage & Escalation Workflow</p>
              </div>
            </div>

            <div className="text-xs text-slate-300 leading-relaxed">
              <FormattedResponse content={result.answer} />
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl text-xs">
            Select any playbook topic above to load procedural guidance.
          </div>
        )}
      </div>
    </div>
  );
}
