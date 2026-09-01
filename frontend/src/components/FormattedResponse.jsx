import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Terminal, Shield, Info, ChevronRight } from 'lucide-react';

function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/90 border-b border-slate-800 text-[11px] text-slate-400 font-mono">
        <div className="flex items-center space-x-1.5">
          <Terminal className="w-3.5 h-3.5 text-blue-400" />
          <span>{language || 'code'}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 px-2 py-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400 text-[10px]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span className="text-[10px]">Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3.5 overflow-x-auto text-[11px] font-mono text-slate-200 leading-relaxed">
        <pre className="!bg-transparent !p-0 !m-0">{value}</pre>
      </div>
    </div>
  );
}

export default function FormattedResponse({ content, className = '' }) {
  if (!content) return null;

  return (
    <div className={`formatted-response space-y-3 text-slate-200 text-xs leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => (
            <div className="mt-4 mb-2 pb-2 border-b border-slate-800 flex items-center space-x-2">
              <div className="w-2 h-5 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full" />
              <h1 className="text-sm sm:text-base font-bold text-white tracking-wide" {...props} />
            </div>
          ),
          h2: ({ node, ...props }) => (
            <div className="mt-4 mb-2.5 p-2.5 bg-slate-900/90 border border-slate-800 border-l-4 border-l-blue-500 rounded-xl flex items-center space-x-2 shadow-sm">
              <Shield className="w-4 h-4 text-blue-400 shrink-0" />
              <h2 className="text-xs sm:text-sm font-bold text-blue-100 uppercase tracking-wide" {...props} />
            </div>
          ),
          h3: ({ node, ...props }) => (
            <div className="mt-3.5 mb-1.5 flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
              <h3 className="text-xs font-bold text-indigo-300 tracking-wide" {...props} />
            </div>
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-[11px] font-semibold text-slate-400 mt-2 mb-1 uppercase tracking-wider" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="my-1.5 leading-relaxed text-slate-300 text-xs" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-semibold text-blue-300 bg-blue-950/40 px-1 py-0.5 rounded border border-blue-800/30 inline-block my-0.5" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="text-slate-300 font-normal italic" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="my-2 space-y-1.5 pl-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="my-2 space-y-2 counter-reset-step pl-1" {...props} />
          ),
          li: ({ node, ordered, index, ...props }) => {
            if (ordered) {
              return (
                <li className="flex items-start space-x-2.5 bg-slate-950/60 border border-slate-800/80 p-2.5 rounded-xl hover:border-slate-700 transition-colors shadow-sm">
                  <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 font-bold text-[10px] shrink-0 mt-0.5">
                    {(index !== undefined ? index + 1 : '•')}
                  </span>
                  <div className="flex-1 text-slate-300 text-xs leading-relaxed" {...props} />
                </li>
              );
            }
            return (
              <li className="flex items-start space-x-2 text-slate-300 text-xs py-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 mt-1.5" />
                <span className="flex-1 leading-relaxed" {...props} />
              </li>
            );
          },
          table: ({ node, ...props }) => (
            <div className="my-3 overflow-x-auto rounded-xl border border-slate-800 shadow-md">
              <table className="min-w-full divide-y divide-slate-800 text-left text-xs" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-900/90 text-slate-300 font-semibold text-[11px] uppercase tracking-wider" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-slate-800/60 bg-slate-950/50" {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="hover:bg-slate-900/40 transition-colors" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="px-3.5 py-2 font-bold text-slate-300" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-3.5 py-2 text-slate-300 font-mono text-[11px]" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <div className="my-3 p-3 bg-amber-500/10 border-l-4 border-amber-500 rounded-r-xl flex items-start space-x-2 text-amber-200 text-xs">
              <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed" {...props} />
            </div>
          ),
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const value = String(children).replace(/\n$/, '');

            if (!inline && (match || value.includes('\n'))) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  value={value}
                />
              );
            }

            return (
              <code
                className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-amber-300 font-mono text-[11px]"
                {...props}
              >
                {children}
              </code>
            );
          },
          hr: () => (
            <hr className="my-4 border-slate-800" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
