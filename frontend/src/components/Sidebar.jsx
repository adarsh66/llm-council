import { useState, useEffect } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="app-logo">
          <span className="logo-icon">⚖️</span>
          <h1>AI Expert Council</h1>
        </div>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Talk to the Council
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title-row">
                <div className="conversation-title">
                  {conv.title || 'New Conversation'}
                </div>
                <button
                  className="conversation-delete-btn"
                  title="Delete conversation"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation && onDeleteConversation(conv.id);
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m1 0v14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6h10z"/>
                  </svg>
                </button>
              </div>
              <div className="conversation-meta">{conv.message_count} messages</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
