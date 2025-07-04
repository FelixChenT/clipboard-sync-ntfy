import React, { useState, useEffect } from 'react';
import './App.css';

// Type definitions
interface Config {
  sender: {
    enabled: boolean;
    ntfy_topic_url: string;
    poll_interval_seconds: number;
    request_timeout_seconds: number;
    filename_prefix: string;
  };
  receiver: {
    enabled: boolean;
    ntfy_server: string;
    ntfy_topic: string;
    reconnect_delay_seconds: number;
    request_timeout_seconds: number;
  };
  logging: {
    level: string;
  };
  macos: {
    image_support: boolean;
  };
}

interface SyncStatus {
  isRunning: boolean;
  pid?: number;
}

interface PythonOutput {
  type: 'stdout' | 'stderr';
  data: string;
}

// Declare global electronAPI
declare global {
  interface Window {
    electronAPI: {
      startSync: (config?: Config) => Promise<{ success: boolean; error?: string }>;
      stopSync: () => Promise<{ success: boolean; error?: string }>;
      getSyncStatus: () => Promise<SyncStatus>;
      getConfig: () => Promise<Config>;
      saveConfig: (config: Config) => Promise<{ success: boolean }>;
      onSyncStatusChanged: (callback: (event: any, data: SyncStatus) => void) => () => void;
      onPythonOutput: (callback: (event: any, data: PythonOutput) => void) => () => void;
    };
  }
}

function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({ isRunning: false });
  const [logs, setLogs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'config' | 'status' | 'logs'>('config');
  const [loading, setLoading] = useState(false);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [configData, statusData] = await Promise.all([
          window.electronAPI.getConfig(),
          window.electronAPI.getSyncStatus()
        ]);
        setConfig(configData);
        setSyncStatus(statusData);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      }
    };

    loadData();

    // Set up event listeners
    const unsubscribeStatus = window.electronAPI.onSyncStatusChanged((event, data) => {
      setSyncStatus(data);
    });

    const unsubscribeOutput = window.electronAPI.onPythonOutput((event, data) => {
      const timestamp = new Date().toLocaleTimeString();
      const logEntry = `[${timestamp}] ${data.type.toUpperCase()}: ${data.data}`;
      setLogs(prev => [...prev.slice(-99), logEntry]); // Keep last 100 logs
    });

    return () => {
      unsubscribeStatus();
      unsubscribeOutput();
    };
  }, []);

  const handleStartSync = async () => {
    if (!config) return;

    setLoading(true);
    try {
      const result = await window.electronAPI.startSync(config);
      if (!result.success) {
        alert(`Failed to start sync: ${result.error}`);
      }
    } catch (error) {
      alert(`Error starting sync: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopSync = async () => {
    setLoading(true);
    try {
      const result = await window.electronAPI.stopSync();
      if (!result.success) {
        alert(`Failed to stop sync: ${result.error}`);
      }
    } catch (error) {
      alert(`Error stopping sync: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!config) return;

    setLoading(true);
    try {
      const result = await window.electronAPI.saveConfig(config);
      if (result.success) {
        alert('Configuration saved successfully!');
      } else {
        alert('Failed to save configuration');
      }
    } catch (error) {
      alert(`Error saving configuration: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = (path: string, value: any) => {
    if (!config) return;

    const keys = path.split('.');
    const newConfig = { ...config };
    let current: any = newConfig;

    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;

    setConfig(newConfig);
  };

  if (!config) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading configuration...</p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Clipboard Sync</h1>
        <div className="status-indicator">
          <div className={`status-dot ${syncStatus.isRunning ? 'running' : 'stopped'}`}></div>
          <span>{syncStatus.isRunning ? 'Running' : 'Stopped'}</span>
          {syncStatus.pid && <span className="pid">PID: {syncStatus.pid}</span>}
        </div>
      </header>

      <nav className="app-nav">
        <button
          className={activeTab === 'config' ? 'active' : ''}
          onClick={() => setActiveTab('config')}
        >
          Configuration
        </button>
        <button
          className={activeTab === 'status' ? 'active' : ''}
          onClick={() => setActiveTab('status')}
        >
          Status
        </button>
        <button
          className={activeTab === 'logs' ? 'active' : ''}
          onClick={() => setActiveTab('logs')}
        >
          Logs
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'config' && (
          <div className="config-panel">
            <h2>Configuration</h2>

            <div className="config-section">
              <h3>Sender Settings</h3>
              <label>
                <input
                  type="checkbox"
                  checked={config.sender.enabled}
                  onChange={(e) => updateConfig('sender.enabled', e.target.checked)}
                />
                Enable Sender
              </label>

              <label>
                Ntfy Topic URL:
                <input
                  type="text"
                  value={config.sender.ntfy_topic_url}
                  onChange={(e) => updateConfig('sender.ntfy_topic_url', e.target.value)}
                  placeholder="https://ntfy.sh/your_topic_here"
                />
              </label>

              <label>
                Poll Interval (seconds):
                <input
                  type="number"
                  value={config.sender.poll_interval_seconds}
                  onChange={(e) => updateConfig('sender.poll_interval_seconds', parseFloat(e.target.value))}
                  min="0.1"
                  step="0.1"
                />
              </label>
            </div>

            <div className="config-section">
              <h3>Receiver Settings</h3>
              <label>
                <input
                  type="checkbox"
                  checked={config.receiver.enabled}
                  onChange={(e) => updateConfig('receiver.enabled', e.target.checked)}
                />
                Enable Receiver
              </label>

              <label>
                Ntfy Server:
                <input
                  type="text"
                  value={config.receiver.ntfy_server}
                  onChange={(e) => updateConfig('receiver.ntfy_server', e.target.value)}
                  placeholder="ntfy.sh"
                />
              </label>

              <label>
                Ntfy Topic:
                <input
                  type="text"
                  value={config.receiver.ntfy_topic}
                  onChange={(e) => updateConfig('receiver.ntfy_topic', e.target.value)}
                  placeholder="your_receive_topic_here"
                />
              </label>
            </div>

            <div className="config-section">
              <h3>Advanced Settings</h3>
              <label>
                Log Level:
                <select
                  value={config.logging.level}
                  onChange={(e) => updateConfig('logging.level', e.target.value)}
                >
                  <option value="DEBUG">Debug</option>
                  <option value="INFO">Info</option>
                  <option value="WARNING">Warning</option>
                  <option value="ERROR">Error</option>
                </select>
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={config.macos.image_support}
                  onChange={(e) => updateConfig('macos.image_support', e.target.checked)}
                />
                Enable macOS Image Support
              </label>
            </div>

            <div className="config-actions">
              <button onClick={handleSaveConfig} disabled={loading}>
                {loading ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'status' && (
          <div className="status-panel">
            <h2>Sync Status</h2>

            <div className="status-info">
              <div className="status-item">
                <strong>Status:</strong>
                <span className={syncStatus.isRunning ? 'status-running' : 'status-stopped'}>
                  {syncStatus.isRunning ? 'Running' : 'Stopped'}
                </span>
              </div>

              {syncStatus.pid && (
                <div className="status-item">
                  <strong>Process ID:</strong> {syncStatus.pid}
                </div>
              )}

              <div className="status-item">
                <strong>Sender:</strong> {config.sender.enabled ? 'Enabled' : 'Disabled'}
              </div>

              <div className="status-item">
                <strong>Receiver:</strong> {config.receiver.enabled ? 'Enabled' : 'Disabled'}
              </div>
            </div>

            <div className="control-buttons">
              <button
                onClick={handleStartSync}
                disabled={loading || syncStatus.isRunning}
                className="start-button"
              >
                {loading ? 'Starting...' : 'Start Sync'}
              </button>

              <button
                onClick={handleStopSync}
                disabled={loading || !syncStatus.isRunning}
                className="stop-button"
              >
                {loading ? 'Stopping...' : 'Stop Sync'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="logs-panel">
            <h2>Logs</h2>

            <div className="logs-actions">
              <button onClick={() => setLogs([])}>Clear Logs</button>
            </div>

            <div className="logs-container">
              {logs.length === 0 ? (
                <p className="no-logs">No logs available. Start sync to see output.</p>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="log-entry">
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
