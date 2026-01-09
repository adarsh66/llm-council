import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);
  const isNearBottomRef = useRef(true);

  // Check if user is near bottom of scroll container
  const checkIfNearBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const threshold = 150;
    const position = container.scrollHeight - container.scrollTop - container.clientHeight;
    return position < threshold;
  }, []);

  // Smart scroll: only auto-scroll if user is near bottom
  const smartScrollToBottom = useCallback(() => {
    if (isNearBottomRef.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'instant' });
    }
  }, []);

  // Track scroll position
  const handleScroll = useCallback(() => {
    isNearBottomRef.current = checkIfNearBottom();
  }, [checkIfNearBottom]);

  // Auto-scroll on new messages/updates
  useEffect(() => {
    smartScrollToBottom();
  }, [conversation, smartScrollToBottom]);

  // Focus textarea when conversation changes
  useEffect(() => {
    if (conversation && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [conversation?.id]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
      // Force scroll after sending
      isNearBottomRef.current = true;
      // Keep focus on textarea
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="messages-container">
          <div className="empty-state">
            <h2>Welcome to the AI Expert Council</h2>
            <p>Create a new conversation to consult with the council</p>
          </div>
        </div>
      </div>
    );
  }

  const hasMessages = conversation.messages.length > 0;
  const hasError = conversation.messages.some(msg => msg.error);

  return (
    <div className="chat-interface">
      <div 
        className="messages-container" 
        ref={messagesContainerRef}
        onScroll={handleScroll}
      >
        <div className="messages-inner">
          {!hasMessages ? (
            <div className="empty-state">
              <h2>Consult the Council</h2>
              <p>Ask a question to receive expert insights from multiple AI perspectives</p>
            </div>
          ) : (
            conversation.messages.map((msg, index) => (
              <div 
                key={index} 
                className={`message-row ${msg.role === 'user' ? 'user' : 'assistant'}`}
              >
                <div className="message-bubble">
                  {msg.role === 'user' ? (
                    <div className="user-bubble">
                      <div className="markdown-content">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <div className="assistant-bubble">
                      <div className="assistant-header">
                        <div className="assistant-icon">⚖️</div>
                        <span className="assistant-label">AI Expert Council</span>
                      </div>
                      <div className="assistant-content">
                        {/* Error banner */}
                        {msg.error && (
                          <div className="error-banner">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                              <path d="M8 1a7 7 0 100 14A7 7 0 008 1zM7 4h2v5H7V4zm0 6h2v2H7v-2z"/>
                            </svg>
                            <span>{msg.error}</span>
                          </div>
                        )}

                        {/* Stage 1 */}
                        {msg.loading?.stage1 && (
                          <div className="stage-loading">
                            <div className="spinner"></div>
                            <span>Collecting individual responses...</span>
                          </div>
                        )}
                        {msg.stage1 && <Stage1 responses={msg.stage1} />}

                        {/* Stage 2 */}
                        {msg.loading?.stage2 && (
                          <div className="stage-loading">
                            <div className="spinner"></div>
                            <span>Running peer rankings...</span>
                          </div>
                        )}
                        {msg.stage2 && (
                          <Stage2
                            rankings={msg.stage2}
                            labelToModel={msg.metadata?.label_to_model}
                            aggregateRankings={msg.metadata?.aggregate_rankings}
                          />
                        )}

                        {/* Stage 3 */}
                        {msg.loading?.stage3 && (
                          <div className="stage-loading">
                            <div className="spinner"></div>
                            <span>Synthesizing final answer...</span>
                          </div>
                        )}
                        {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {isLoading && !conversation.messages.some(m => m.loading) && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <span>Consulting the council...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Always show composer when conversation is selected */}
      <div className="input-form-wrapper">
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder="Ask the council... (Enter to send, Shift+Enter for new line)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
