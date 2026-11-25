import React from 'react';

interface SystemPromptProps {
  value: string;
  onChange: (value: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const SystemPrompt: React.FC<SystemPromptProps> = ({ value, onChange, isOpen, onToggle }) => {
  const hasValue = value.trim().length > 0;

  return (
    <div className="composer-popover-anchor">
      <button
        type="button"
        className={`composer-pill-btn ${isOpen ? 'active' : ''} ${hasValue ? 'has-value' : ''}`}
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="pill-icon">⚙️</span>
        <span className="pill-label">System Prompt</span>
        {hasValue && <span className="active-dot" title="Custom system prompt active" />}
      </button>

      {isOpen && (
        <div className="composer-popover-panel">
          <div className="popover-panel-header">
            <span className="popover-title">System Instructions</span>
            {hasValue && (
              <button
                type="button"
                className="btn-clear-link"
                onClick={() => onChange('')}
              >
                Clear
              </button>
            )}
          </div>
          <p className="popover-desc">
            Define system instructions sent with every turn without cluttering chat history.
          </p>
          <textarea
            data-testid="system-prompt-input"
            className="popover-textarea"
            placeholder="e.g. You are a senior AI engineer. Answer concisely..."
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={3}
            autoFocus
          />
        </div>
      )}
    </div>
  );
};
