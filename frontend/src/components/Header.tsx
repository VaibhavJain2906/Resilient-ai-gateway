import React from 'react';
import { HealthResponse } from '../types';

interface HeaderProps {
  sessionId: string;
  health: HealthResponse | null;
  onNewSession: () => void;
}

export const Header: React.FC<HeaderProps> = ({ sessionId, health, onNewSession }) => {
  return (
    <header className="widget-header">
      <div className="brand-group">
        <div className="brand-avatar" aria-hidden="true">
          <span className="brand-avatar-glyph">✦</span>
        </div>
        <div className="brand-text">
          <h1 className="brand-title">Resilient AI</h1>
          <p className="brand-subtitle">
            <span className="gateway-badge">GATEWAY</span>
            <span>LLM chat with intelligent failover &amp; caching</span>
          </p>
        </div>
      </div>

      <div className="header-actions">
        {/* Subtle status & session info */}
        <div className="header-status-pill" title="Gateway connection & session info">
          <span className={`status-dot ${health ? 'online' : 'connecting'}`} />
          <span className="health-label">
            {health
              ? `Online • ${health.keys_configured} keys • Cache active`
              : 'Connecting...'}
          </span>
          <span className="status-separator">|</span>
          <span className="session-tag" title={`Session ID: ${sessionId}`}>
            <span className="session-prefix">s:</span>
            <span className="session-val">{sessionId.slice(0, 8)}…</span>
          </span>
        </div>

        {/* New Chat Button */}
        <button
          type="button"
          className="btn-new-chat"
          onClick={onNewSession}
          title="Start fresh conversation"
        >
          + New Chat
        </button>
      </div>
    </header>
  );
};
