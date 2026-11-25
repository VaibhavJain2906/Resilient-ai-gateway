import { ChatResponse, HealthResponse, SimulationMode } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  systemPrompt?: string,
  simulationMode: SimulationMode = 'normal'
): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (simulationMode === 'key_1_429') {
    headers['X-Simulate-Failure'] = 'key_1=429';
  } else if (simulationMode === 'wildcard_429') {
    headers['X-Simulate-Failure'] = '*=429';
  }

  const payload: { session_id: string; message: string; system_prompt?: string } = {
    session_id: sessionId,
    message: message.trim(),
  };

  if (systemPrompt && systemPrompt.trim()) {
    payload.system_prompt = systemPrompt.trim();
  }

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    if (res.status === 503) {
      throw new Error(data?.detail || 'All AI providers are temporarily unavailable. Please try again.');
    } else if (res.status === 422) {
      const msg = Array.isArray(data?.detail)
        ? data.detail.map((e: { msg?: string }) => e.msg).join('; ')
        : data?.detail || 'Validation error on message parameters.';
      throw new Error(`Validation error: ${msg}`);
    } else if (res.status === 404) {
      throw new Error(data?.detail || 'Resource not found.');
    }
    throw new Error(data?.detail || `Server error (${res.status}). Please try again.`);
  }

  return data as ChatResponse;
}
