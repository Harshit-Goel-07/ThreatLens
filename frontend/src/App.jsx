import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import CopilotChat from './components/CopilotChat';
import AlertExplainer from './components/AlertExplainer';
import CveLookup from './components/CveLookup';
import PlaybookGuide from './components/PlaybookGuide';
import IngestionHub from './components/IngestionHub';
import SystemHealth from './components/SystemHealth';
import { getCurrentUser, loginUser } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [user, setUser] = useState(null);
  const [authType, setAuthType] = useState('none');
  const [systemStatus, setSystemStatus] = useState('healthy');

  const checkAuthStatus = async () => {
    const token = localStorage.getItem('token');
    let apiKey = localStorage.getItem('apiKey');

    if (token) {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        setAuthType('jwt');
        return;
      } catch (e) {
        localStorage.removeItem('token');
      }
    }

    if (!apiKey) {
      apiKey = 'test-api-key-12345';
      localStorage.setItem('apiKey', apiKey);
    }

    if (apiKey) {
      setUser({ subject: 'Service Principal', role: 'service' });
      setAuthType('apikey');
      return;
    }

    setUser(null);
    setAuthType('none');
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const handleLogin = async (email, password) => {
    await loginUser(email, password);
    await checkAuthStatus();
  };

  const handleApiKeySave = (key) => {
    localStorage.setItem('apiKey', key);
    localStorage.removeItem('token');
    checkAuthStatus();
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('apiKey');
    setUser(null);
    setAuthType('none');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Header
        user={user}
        authType={authType}
        onLogin={handleLogin}
        onApiKeySave={handleApiKeySave}
        onLogout={handleLogout}
        systemStatus={systemStatus}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 flex flex-col overflow-hidden">
          {activeTab === 'chat' && <CopilotChat />}
          {activeTab === 'alert' && <AlertExplainer />}
          {activeTab === 'cve' && <CveLookup />}
          {activeTab === 'playbooks' && <PlaybookGuide />}
          {activeTab === 'ingestion' && <IngestionHub />}
          {activeTab === 'health' && <SystemHealth onStatusUpdate={setSystemStatus} />}
        </main>
      </div>
    </div>
  );
}
