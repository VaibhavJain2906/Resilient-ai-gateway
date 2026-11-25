import React, { useState, useRef, useEffect } from 'react';
import { SimulationMode } from '../types';
import { SystemPrompt } from './SystemPrompt';
import { DemoControls } from './DemoControls';

interface ChatComposerProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  systemPrompt: string;
  onSystemPromptChange: (value: string) => void;
  simulationMode: SimulationMode;
  onSimulationModeChange: (mode: SimulationMode) => void;
}

const MAX_CHAR_LIMIT = 4000;

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  isLoading,
  systemPrompt,
  onSystemPromptChange,
  simulationMode,
  onSimulationModeChange,
}) => {
  const [text, setText] = useState('');
  const [activePopover, setActivePopover] = useState<'prompt' | 'demo' | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmed = text.trim();
  const charCount = text.length;
  const isOverLimit = charCount > MAX_CHAR_LIMIT;
  const canSend = trimmed.length > 0 && !isOverLimit && !isLoading;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!canSend) return;

    onSend(trimmed);
    setText('');
    setActivePopover(null); // Close popovers on submit
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="floating-composer-shell">
      <form onSubmit={handleSubmit} className="floating-composer-card">
        {/* Top: Input row with embedded send action */}
        <div className="composer-input-row">
          <textarea
            ref={textareaRef}
            data-testid="chat-input"
            className="composer-textarea"
            placeholder="Message Resilient AI... (Enter to send, Shift+Enter for newline)"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            aria-label="Message Resilient AI"
          />

          <button
            type="submit"
            data-testid="send-button"
            className={`circular-send-btn ${canSend ? 'ready' : ''}`}
            disabled={!canSend}
            title={canSend ? 'Send message' : 'Enter a message to send'}
            aria-label="Send message"
          >
            {isLoading ? (
              <span className="spinner-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            ) : (
              <svg
                className="send-arrow-svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </button>
        </div>

        {/* Bottom toolbar inside composer */}
        <div className="composer-bottom-bar">
          <div className="composer-controls-group">
            <SystemPrompt
              value={systemPrompt}
              onChange={onSystemPromptChange}
              isOpen={activePopover === 'prompt'}
              onToggle={() =>
                setActivePopover((prev) => (prev === 'prompt' ? null : 'prompt'))
              }
            />

            <DemoControls
              mode={simulationMode}
              onChange={onSimulationModeChange}
              isOpen={activePopover === 'demo'}
              onToggle={() =>
                setActivePopover((prev) => (prev === 'demo' ? null : 'demo'))
              }
            />
          </div>

          <div className="composer-meta-group">
            <span
              className={`char-counter ${
                isOverLimit ? 'over' : charCount > 3500 ? 'near' : ''
              }`}
            >
              {charCount} / {MAX_CHAR_LIMIT}
            </span>
          </div>
        </div>
      </form>
    </div>
  );
};
