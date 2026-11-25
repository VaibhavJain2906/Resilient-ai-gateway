import React from 'react';
import { ChatMetadata } from '../types';

interface MessageMetadataProps {
  metadata: ChatMetadata;
}

export const MessageMetadata: React.FC<MessageMetadataProps> = ({ metadata }) => {
  const isCache = metadata.resolution_source === 'LLM_CACHE';
  const hasFallback = metadata.fallback_attempts > 0;

  return (
    <div className="metadata-container">
      {/* Primary Line: Source badge + Model + Latency */}
      <div className="metadata-primary-line">
        <span
          data-testid="meta-source"
          className={`source-badge ${isCache ? 'badge-cache' : 'badge-live'}`}
        >
          {metadata.resolution_source}
        </span>

        <span data-testid="meta-model" className="meta-info meta-model-name">
          {metadata.model}
        </span>

        <span className="meta-dot">·</span>

        <span data-testid="meta-latency" className="meta-info meta-latency-val">
          {metadata.latency_ms.toLocaleString()} ms
        </span>
      </div>

      {/* Secondary Line: Tokens · Key · Fallbacks */}
      <div className="metadata-secondary-line">
        <span className="meta-secondary-item">
          Input <span data-testid="meta-input-tokens">{metadata.input_tokens}</span>
        </span>
        <span className="meta-dot">·</span>
        <span className="meta-secondary-item">
          Output <span data-testid="meta-output-tokens">{metadata.output_tokens}</span>
        </span>
        <span className="meta-dot">·</span>
        <span className="meta-secondary-item">
          Key {metadata.key_id ? metadata.key_id : '—'}
        </span>
        <span className="meta-dot">·</span>
        <span className={`meta-secondary-item ${hasFallback ? 'fallback-warning' : ''}`}>
          {metadata.fallback_attempts} fallback{metadata.fallback_attempts === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  );
};
