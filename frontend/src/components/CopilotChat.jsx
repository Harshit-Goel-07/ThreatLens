import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Database, FileText, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { queryCopilotStream, apiFetch } from '../api/client';

const SAMPLE_PROMPTS = [
  "How to investigate and remediate Command & Scripting Interpreter (MITRE T1059)?",
  "Explain Log4Shell (CVE-2021-44228) and how to detect it in security logs.",
  "What is the SOC playbook for responding to a Ransomware outbreak?",
  "Analyze this Sysmon log for potential privilege escalation.",
];

export default function CopilotChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState(['mitre', 'cve', 'logs', 'playbooks']);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleSource = (source) => {
    setSelectedSources((prev) =>
      prev.includes(source)
        ? prev.filter((s) => s !== source)
        : [...prev, source]
    );
  };

  const handleSend = async (queryText = input) => {
    const query = queryText.trim();
    if (!query || isLoading) return;

    const userMessage = { role: 'user', content: query, timestamp: new Date().toLocaleTimeString() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    let assistantMessage = {
      role: 'assistant',
      content: '',
      sources: [],
      confidence: 0,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, assistantMessage]);

    await queryCopilotStream(
      {
        query,
        source_types: selectedSources,
        top_k: 5,
        rerank_top_k: 3,
      },
      (chunk) => {
        if (chunk.content) {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: updated[lastIdx].content + chunk.content,
            };
            return updated;
          });
        }
        if (chunk.sources) {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            updated[lastIdx] = {
              ...updated[lastIdx],
              sources: chunk.sources,
            };
            return updated;
          });
        }
      },
      (err) => {
        console.error('Stream error:', err);
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: updated[lastIdx].content || `Query completed with fallback note. (${err.message})`,
          };
          return updated;
        });
        setIsLoading(false);
      },
      () => {
        setIsLoading(false);
      }
    );
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-slate-950 overflow-hidden">
      {/* Top Filter Toolbar */}
      <div className="bg-slate-900/60 border-b border-slate-800/80 px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-xs">
          <Database className="w-4 h-4 text-blue-400 mr-1" />
          <span className="text-slate-400 font-medium">Data Sources:</span>
          {['mitre', 'cve', 'logs', 'playbooks'].map((src) => {
            const isSelected = selectedSources.includes(src);
            return (
              <button
                key={src}
                onClick={() => toggleSource(src)}
                className={`px-2.5 py-1 rounded-lg font-medium capitalize text-[11px] transition-all border ${
                  isSelected
                    ? 'bg-blue-600/20 text-blue-300 border-blue-500/40 shadow-sm'
                    : 'bg-slate-900 text-slate-500 border-slate-800 hover:text-slate-300'
                }`}
              >
                {src}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setMessages([])}
          className="text-xs text-slate-500 hover:text-slate-300 flex items-center space-x-1"
          title="Clear Conversation"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Clear Chat</span>
        </button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto text-center py-12 space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600/20 to-purple-600/20 border border-blue-500/20 flex items-center justify-center mx-auto shadow-xl">
              <Sparkles className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Security Copilot AI Assistant</h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Ask any questions regarding MITRE ATT&CK techniques, CVE vulnerabilities, security logs analysis, or incident playbooks.
              </p>
            </div>

            {/* Prompt Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-left">
              {SAMPLE_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-xs text-slate-300 transition-all text-left group"
                >
                  <p className="font-medium group-hover:text-blue-400 transition-colors">{prompt}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`flex items-start space-x-3 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shrink-0 shadow-md shadow-blue-600/20 mt-1">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}

              <div
                className={`max-w-3xl rounded-2xl p-4 text-xs space-y-3 shadow-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white font-medium rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                }`}
              >
                <div className="flex items-center justify-between border-b border-slate-800/60 pb-2 text-[10px] text-slate-400">
                  <span className="font-bold text-slate-300">{msg.role === 'user' ? 'SOC Analyst' : 'Security Copilot'}</span>
                  <span>{msg.timestamp}</span>
                </div>

                <div className="whitespace-pre-wrap leading-relaxed">
                  {msg.content || (
                    <div className="flex items-center space-x-2 text-slate-400">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />
                      <span>Synthesizing response from RAG context...</span>
                    </div>
                  )}
                </div>

                {/* Sources & Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2">
                    <div className="flex items-center space-x-1 text-[11px] font-semibold text-blue-400">
                      <FileText className="w-3.5 h-3.5" />
                      <span>Retrieved Context ({msg.sources.length})</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.sources.map((src, i) => (
                        <div
                          key={i}
                          className="p-2 bg-slate-950/80 border border-slate-800 rounded-lg text-[10px] space-y-1"
                        >
                          <div className="font-semibold text-slate-200 truncate">{src.title || src.doc_id || `Source #${i+1}`}</div>
                          <div className="text-slate-400 flex items-center justify-between">
                            <span className="capitalize text-blue-300">{src.source_type || 'document'}</span>
                            {src.score && <span>Score: {(src.score * 100).toFixed(0)}%</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-5 h-5 text-slate-300" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-slate-900/80 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="max-w-4xl mx-auto flex items-center space-x-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Ask a security question, paste alert JSON, or query CVEs..."
            className="flex-1 px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold rounded-xl text-xs transition-all shadow-md shadow-blue-600/20 flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
