import React, { useState } from 'react';
import { Shield, Key, Lock, LogOut, User, Activity, Sparkles } from 'lucide-react';

export default function Header({ user, authType, onLogin, onApiKeySave, onLogout, systemStatus }) {
  const [showAuthModal, setShowAuthModal] = useState(!user && !localStorage.getItem('apiKey') && !localStorage.getItem('token'));
  const [mode, setMode] = useState('apikey'); // 'apikey' or 'login'
  const [apiKeyInput, setApiKeyInput] = useState(localStorage.getItem('apiKey') || '');
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      if (mode === 'apikey') {
        if (!apiKeyInput.trim()) return;
        onApiKeySave(apiKeyInput.trim());
        setShowAuthModal(false);
      } else {
        await onLogin(emailInput.trim(), passwordInput.trim());
        setShowAuthModal(false);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed');
    }
  };

  return (
    <>
      <header className="h-16 bg-slate-900/90 border-b border-slate-800 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-purple-600 p-0.5 shadow-lg shadow-blue-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
                ThreatLens
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full flex items-center space-x-1">
                <Sparkles className="w-3 h-3 inline mr-1" /> SOC AI v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Incident Response & Threat Intelligence</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Health status pill */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1 bg-slate-850 rounded-lg border border-slate-800 text-xs">
            <span className={`w-2 h-2 rounded-full ${systemStatus === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span className="text-slate-300 font-medium capitalize">System {systemStatus || 'Online'}</span>
          </div>

          {/* Auth State Button */}
          {user ? (
            <div className="flex items-center space-x-3 bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs">
              <div className="w-6 h-6 rounded-full bg-indigo-600/30 flex items-center justify-center text-indigo-400 font-bold">
                {user.role === 'admin' ? 'A' : 'S'}
              </div>
              <div className="text-left">
                <div className="text-slate-200 font-medium capitalize">{user.subject || user.role || 'Analyst'}</div>
                <div className="text-[10px] text-slate-400">{authType === 'jwt' ? 'JWT Session' : 'Service API Key'}</div>
              </div>
              <button
                onClick={onLogout}
                className="text-slate-400 hover:text-rose-400 transition-colors ml-2 p-1"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-600/20 transition-all flex items-center space-x-1.5"
            >
              <Key className="w-3.5 h-3.5" />
              <span>Authenticate</span>
            </button>
          )}
        </div>
      </header>

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-center mb-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center">
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
            </div>

            <h2 className="text-xl font-bold text-white text-center mb-1">Access ThreatLens</h2>
            <p className="text-xs text-slate-400 text-center mb-6">Authenticate via Service API Key or User Account</p>

            <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-xl mb-5 text-xs">
              <button
                type="button"
                onClick={() => setMode('apikey')}
                className={`py-2 rounded-lg font-medium transition-all ${
                  mode === 'apikey' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                API Key
              </button>
              <button
                type="button"
                onClick={() => setMode('login')}
                className={`py-2 rounded-lg font-medium transition-all ${
                  mode === 'login' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                Account Login
              </button>
            </div>

            {errorMsg && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-xs">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              {mode === 'apikey' ? (
                <div>
                  <label className="block text-slate-300 font-medium mb-1.5">X-API-Key</label>
                  <input
                    type="password"
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    placeholder="Enter API Key (e.g. test-api-key-12345)"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    required
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Default dev key: <code className="text-blue-400">admin</code> or <code className="text-blue-400">test-api-key-12345</code></p>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1.5">Email / Username</label>
                    <input
                      type="text"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      placeholder="admin or admin@seccopilot.local"
                      className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1.5">Password</label>
                    <input
                      type="password"
                      value={passwordInput}
                      onChange={(e) => setPasswordInput(e.target.value)}
                      placeholder="admin"
                      className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                      required
                    />
                    <p className="text-[10px] text-slate-500 mt-1">Default dev account: <code className="text-blue-400">admin</code> / <code className="text-blue-400">admin</code></p>
                  </div>
                </>
              )}

              <div className="flex space-x-2 pt-2">
                {(user || localStorage.getItem('apiKey')) && (
                  <button
                    type="button"
                    onClick={() => setShowAuthModal(false)}
                    className="flex-1 py-2.5 bg-slate-800 text-slate-300 rounded-lg font-medium hover:bg-slate-700 transition-colors"
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold shadow-lg shadow-blue-600/20 transition-all flex items-center justify-center space-x-2"
                >
                  <Lock className="w-4 h-4" />
                  <span>Authenticate</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
