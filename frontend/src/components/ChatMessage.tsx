import React from 'react';
import { Message } from '../types';
import { MessageMetadata } from './MessageMetadata';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="chat-row user-row">
        <div className="user-bubble-container">
          <div className="user-bubble">
            <div className="user-message-text">{message.content}</div>
          </div>
          <div className="user-message-time">{message.timestamp}</div>
        </div>
      </div>
    );
  }

  // Assistant message container with required data-testid="assistant-message"
  return (
    <div
      data-testid="assistant-message"
      className={`chat-row assistant-row ${message.isError ? 'has-error' : ''}`}
    >
      <div className="assistant-avatar-badge" aria-hidden="true">
        {message.isError ? '!' : '✦'}
      </div>

      <div className="assistant-content-container">
        <div className={`assistant-body-text ${message.isError ? 'error-text' : ''}`}>
          {message.content}
        </div>

        {/* Clean, quiet technical footer */}
        {message.metadata && !message.isError && (
          <MessageMetadata metadata={message.metadata} />
        )}

        <div className="assistant-time">{message.timestamp}</div>
      </div>
    </div>
  );
};
