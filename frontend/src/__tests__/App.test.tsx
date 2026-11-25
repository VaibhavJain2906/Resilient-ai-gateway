import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as api from '../services/api';

describe('Resilient AI Frontend Component & Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Default mock health check
    vi.spyOn(api, 'fetchHealth').mockResolvedValue({
      status: 'ok',
      keys_configured: 2,
      cache_enabled: true,
    });
  });

  it('renders application header, title, and initial session ID', async () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Resilient AI' })).toBeInTheDocument();
    expect(screen.getByText(/LLM chat with intelligent failover/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Online • 2 keys • Cache active/i)).toBeInTheDocument();
    });

    const sessionElements = screen.getByText('s:');
    expect(sessionElements).toBeInTheDocument();
  });

  it('renders minimal empty state with starter prompts', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Online • 2 keys • Cache active/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Chat through a resilient LLM gateway with automatic failover and caching/i)).toBeInTheDocument();
    expect(screen.getByText(/What is the capital of France\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Explain caching in one sentence/i)).toBeInTheDocument();
    expect(screen.getByText(/Give me a Python tip/i)).toBeInTheDocument();
  });

  it('contains required input and send button data-testid attributes', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Online • 2 keys • Cache active/i)).toBeInTheDocument();
    });

    const input = screen.getByTestId('chat-input');
    const sendButton = screen.getByTestId('send-button');

    expect(input).toBeInTheDocument();
    expect(sendButton).toBeInTheDocument();
    // Empty input -> disabled button
    expect(sendButton).toBeDisabled();
  });

  it('contains data-testid="system-prompt-input" when expanding system prompt settings', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Online • 2 keys • Cache active/i)).toBeInTheDocument();
    });

    const systemPromptToggle = screen.getByText('System Prompt');
    fireEvent.click(systemPromptToggle);

    const systemPromptInput = screen.getByTestId('system-prompt-input');
    expect(systemPromptInput).toBeInTheDocument();

    fireEvent.change(systemPromptInput, { target: { value: 'Be a pirate' } });
    expect(systemPromptInput).toHaveValue('Be a pirate');
  });

  it('allows selecting Demo Failure Simulation modes', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Online • 2 keys • Cache active/i)).toBeInTheDocument();
    });

    const demoToggle = screen.getByText('Demo Failure Simulation');
    fireEvent.click(demoToggle);

    const normalRadio = screen.getByLabelText(/Normal/i);
    const key1Radio = screen.getByLabelText(/Simulate key_1 \(429\)/i);
    const wildcardRadio = screen.getByLabelText(/Simulate All Keys \(429\)/i);

    expect(normalRadio).toBeChecked();

    fireEvent.click(key1Radio);
    expect(key1Radio).toBeChecked();

    fireEvent.click(wildcardRadio);
    expect(wildcardRadio).toBeChecked();
  });

  it('sends message, clears input, and renders assistant message with required testids for LIVE_INFERENCE', async () => {
    const mockSend = vi.spyOn(api, 'sendChatMessage').mockResolvedValue({
      session_id: 's-test',
      reply: 'Paris is the capital of France.',
      metadata: {
        resolution_source: 'LIVE_INFERENCE',
        model: 'gemini/gemini-3-flash-preview',
        latency_ms: 1882,
        input_tokens: 21,
        output_tokens: 53,
        key_id: 'key_1',
        fallback_attempts: 0,
      },
    });

    render(<App />);

    const input = screen.getByTestId('chat-input');
    const sendButton = screen.getByTestId('send-button');

    fireEvent.change(input, { target: { value: 'What is the capital of France?' } });
    expect(sendButton).not.toBeDisabled();

    fireEvent.click(sendButton);

    // Input should clear immediately after send
    expect(input).toHaveValue('');

    // Wait for assistant response to render
    await waitFor(() => {
      expect(screen.getByTestId('assistant-message')).toBeInTheDocument();
    });

    const assistantMsg = screen.getByTestId('assistant-message');
    expect(assistantMsg).toHaveTextContent('Paris is the capital of France.');

    // Verify EXACT testid values inside assistant container
    const metaSource = screen.getByTestId('meta-source');
    expect(metaSource).toHaveTextContent('LIVE_INFERENCE');
    expect(metaSource.textContent).toBe('LIVE_INFERENCE');

    const metaModel = screen.getByTestId('meta-model');
    expect(metaModel).toHaveTextContent('gemini/gemini-3-flash-preview');

    const metaLatency = screen.getByTestId('meta-latency');
    expect(metaLatency).toHaveTextContent('1,882 ms');

    const metaInputTokens = screen.getByTestId('meta-input-tokens');
    expect(metaInputTokens).toHaveTextContent('21');

    const metaOutputTokens = screen.getByTestId('meta-output-tokens');
    expect(metaOutputTokens).toHaveTextContent('53');

    expect(screen.getByText(/Key key_1/i)).toBeInTheDocument();
    expect(screen.getByText(/0 fallbacks/i)).toBeInTheDocument();

    expect(mockSend).toHaveBeenCalledWith(
      expect.stringMatching(/^s-/),
      'What is the capital of France?',
      '',
      'normal'
    );
  });

  it('renders required metadata for LLM_CACHE hit with null key_id (Key —)', async () => {
    vi.spyOn(api, 'sendChatMessage').mockResolvedValue({
      session_id: 's-test-cache',
      reply: 'Cached answer',
      metadata: {
        resolution_source: 'LLM_CACHE',
        model: 'gemini/gemini-3-flash-preview',
        latency_ms: 68,
        input_tokens: 21,
        output_tokens: 53,
        key_id: null,
        fallback_attempts: 0,
      },
    });

    render(<App />);

    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'Same question' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByTestId('assistant-message')).toBeInTheDocument();
    });

    const metaSource = screen.getByTestId('meta-source');
    expect(metaSource.textContent).toBe('LLM_CACHE');

    expect(screen.getByTestId('meta-latency')).toHaveTextContent('68 ms');
    expect(screen.getByText(/Key —/i)).toBeInTheDocument();
  });

  it('renders failover metadata showing key_2 and 1 fallback attempt', async () => {
    vi.spyOn(api, 'sendChatMessage').mockResolvedValue({
      session_id: 's-failover',
      reply: 'FAILOVER_OK',
      metadata: {
        resolution_source: 'LIVE_INFERENCE',
        model: 'gemini/gemini-3-flash-preview',
        latency_ms: 1440,
        input_tokens: 15,
        output_tokens: 37,
        key_id: 'key_2',
        fallback_attempts: 1,
      },
    });

    render(<App />);

    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'Trigger failover' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByTestId('assistant-message')).toBeInTheDocument();
    });

    expect(screen.getByText(/Key key_2/i)).toBeInTheDocument();
    expect(screen.getByText(/1 fallback/i)).toBeInTheDocument();
  });

  it('displays user-friendly error message on 503 provider unavailability without crashing', async () => {
    vi.spyOn(api, 'sendChatMessage').mockRejectedValue(
      new Error('All AI providers are temporarily unavailable. Please try again.')
    );

    render(<App />);

    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'This will fail' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByText(/All AI providers are temporarily unavailable/i)).toBeInTheDocument();
    });

    // App composer remains usable
    expect(input).toBeEnabled();
  });

  it('starts a new session and clears messages when "+ New Chat" is clicked', async () => {
    vi.spyOn(api, 'sendChatMessage').mockResolvedValue({
      session_id: 's-first',
      reply: 'First reply',
      metadata: {
        resolution_source: 'LIVE_INFERENCE',
        model: 'gemini/gemini-3-flash-preview',
        latency_ms: 100,
        input_tokens: 10,
        output_tokens: 5,
        key_id: 'key_1',
        fallback_attempts: 0,
      },
    });

    render(<App />);

    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'First message' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByText('First reply')).toBeInTheDocument();
    });

    // Click "+ New Chat"
    const newChatBtn = screen.getByRole('button', { name: /\+ New Chat/i });
    fireEvent.click(newChatBtn);

    // Messages should be cleared and empty state returned
    expect(screen.queryByText('First reply')).not.toBeInTheDocument();
    expect(screen.getByText(/Chat through a resilient LLM gateway/i)).toBeInTheDocument();
  });
});
