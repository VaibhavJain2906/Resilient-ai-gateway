import { useState, useEffect, useRef } from 'react';
import { Message, HealthResponse, SimulationMode } from './types';
import { fetchHealth, sendChatMessage } from './services/api';
import { Header } from './components/Header';
import { EmptyState } from './components/EmptyState';
import { ChatMessage } from './components/ChatMessage';
import { ChatComposer } from './components/ChatComposer';

function generateSessionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `s-${crypto.randomUUID()}`;
  }
  return `s-${Math.random().toString(36).substring(2, 12)}`;
}

export function App() {
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());
  const [messages, setMessages] = useState<Message[]>([]);
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [simulationMode, setSimulationMode] = useState<SimulationMode>('normal');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Health probe on mount
  useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));
  }, []);

  // Smooth scroll to latest turn
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleNewSession = () => {
    setSessionId(generateSessionId());
    setMessages([]);
    setIsLoading(false);
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        sessionId,
        text,
        systemPrompt,
        simulationMode
      );

      const assistantMessage: Message = {
        id: `ast-${Date.now()}`,
        role: 'assistant',
        content: response.reply,
        metadata: response.metadata,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred.';
      const errorAssistantMessage: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: errorMessage,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };
      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-viewport">
      <div className="chat-app-shell">
        {/* Simplified Header */}
        <Header
          sessionId={sessionId}
          health={health}
          onNewSession={handleNewSession}
        />

        {/* Dominant Chat Stage */}
        <main className="chat-stage" aria-live="polite">
          {messages.length === 0 ? (
            <EmptyState onSelectPrompt={handleSendMessage} />
          ) : (
            <div className="message-list">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
            </div>
          )}

          {/* Typing indicator */}
          {isLoading && (
            <div className="chat-row assistant-row typing-row">
              <div className="assistant-avatar-badge" aria-hidden="true">✦</div>
              <div className="typing-dots-pill">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* Floating Integrated Composer */}
        <ChatComposer
          onSend={handleSendMessage}
          isLoading={isLoading}
          systemPrompt={systemPrompt}
          onSystemPromptChange={setSystemPrompt}
          simulationMode={simulationMode}
          onSimulationModeChange={setSimulationMode}
        />
      </div>
    </div>
  );
}

export default App;
