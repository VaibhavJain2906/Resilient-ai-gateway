import React from 'react';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

const STARTER_PROMPTS = [
  'What is the capital of France? Reply with only the city name.',
  'Explain caching in one sentence.',
  'Give me a Python tip.',
];

export const EmptyState: React.FC<EmptyStateProps> = ({ onSelectPrompt }) => {
  return (
    <div className="conversational-empty-state">
      <div className="empty-avatar-circle" aria-hidden="true">
        <span className="empty-avatar-glyph">✦</span>
      </div>

      <h2 className="empty-title">How can I help?</h2>
      <p className="empty-description">
        Chat through a resilient LLM gateway with automatic failover and caching.
      </p>

      <div className="quick-replies-group">
        {STARTER_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            className="quick-reply-pill"
            onClick={() => onSelectPrompt(prompt)}
          >
            <span className="quick-reply-arrow">→</span>
            <span className="quick-reply-text">{prompt}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
